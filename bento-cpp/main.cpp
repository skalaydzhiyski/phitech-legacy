#include <netinet/in.h>
#include <resolv.h>
#include <unistd.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <databento/constants.hpp>  // dataset, kUndefPrice
#include <databento/datetime.hpp>   // ToIso8601, UnixNanos
#include <databento/dbn_file_store.hpp>
#include <databento/enums.hpp>        // Action, Side
#include <databento/fixed_price.hpp>  // PxToString
#include <databento/flag_set.hpp>
#include <databento/historical.hpp>  // HistoricalBuilder
#include <databento/record.hpp>      // BidAskPair, MboMsg, Record
#include <databento/timeseries.hpp>
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <nlohmann/detail/output/output_adapters.hpp>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace databento;

struct Order {
    uint64_t id;
    UnixNanos ts_event;
    int64_t price;
    uint32_t size;
    Side side;
    bool is_tob;
};

struct PriceLevel {
    int64_t price{kUndefPrice};
    uint32_t size{0};
    uint32_t count{0};

    bool IsEmpty() const { return price == kUndefPrice; }
    operator bool() const { return !IsEmpty(); }
};

std::ostream& operator<<(std::ostream& stream, const PriceLevel& level) {
    stream << level.size << " @ " << PxToString(level.price) << " | " << level.count << " order(s)";
    return stream;
}

class Book {
   public:
    std::pair<PriceLevel, PriceLevel> Bbo() const { return {GetBidLevel(), GetAskLevel()}; }

    PriceLevel GetBidLevel(std::size_t idx = 0) const {
        if (bids_.size() > idx) {
            // Reverse iterator to get highest bid prices first
            auto level_it = bids_.rbegin();
            std::advance(level_it, idx);
            return GetPriceLevel(level_it->first, level_it->second);
        }
        return PriceLevel{};
    }

    PriceLevel GetAskLevel(std::size_t idx = 0) const {
        if (offers_.size() > idx) {
            auto level_it = offers_.begin();
            std::advance(level_it, idx);
            return GetPriceLevel(level_it->first, level_it->second);
        }
        return PriceLevel{};
    }

    PriceLevel GetBidLevelByPx(int64_t px) const {
        auto level_it = bids_.find(px);
        if (level_it == bids_.end()) {
            throw std::invalid_argument{"No bid level at " + PxToString(px)};
        }
        return GetPriceLevel(px, level_it->second);
    }

    PriceLevel GetAskLevelByPx(int64_t px) const {
        auto level_it = offers_.find(px);
        if (level_it == offers_.end()) {
            throw std::invalid_argument{"No ask level at " + PxToString(px)};
        }
        return GetPriceLevel(px, level_it->second);
    }

    std::vector<BidAskPair> GetSnapshot(std::size_t level_count = 1) const {
        std::vector<BidAskPair> res;
        for (size_t i = 0; i < level_count; ++i) {
            BidAskPair ba_pair{kUndefPrice, kUndefPrice, 0, 0, 0, 0};
            auto bid = GetBidLevel(i);
            if (bid) {
                ba_pair.bid_px = bid.price;
                ba_pair.bid_sz = bid.size;
                ba_pair.bid_ct = bid.count;
            }
            auto ask = GetAskLevel(i);
            if (ask) {
                ba_pair.ask_px = ask.price;
                ba_pair.ask_sz = ask.size;
                ba_pair.ask_ct = ask.count;
            }
            res.emplace_back(ba_pair);
        }
        return res;
    }

    void Apply(const MboMsg& mbo_msg) {
        switch (mbo_msg.action) {
            case Action::Trade:
            case Action::Fill: {
                break;
            }
            case Action::Clear: {
                Clear();
                break;
            }
            case Action::Add: {
                Add(mbo_msg.hd.ts_event, mbo_msg.side, mbo_msg.order_id, mbo_msg.price,
                    mbo_msg.size, mbo_msg.flags);
                break;
            }
            case Action::Cancel: {
                Cancel(mbo_msg.side, mbo_msg.order_id, mbo_msg.price, mbo_msg.size);
                break;
            }
            case Action::Modify: {
                Modify(mbo_msg.hd.ts_event, mbo_msg.side, mbo_msg.order_id, mbo_msg.price,
                       mbo_msg.size, mbo_msg.flags);
                break;
            }
            default: {
                throw std::invalid_argument{std::string{"Unknown action: "} +
                                            ToString(mbo_msg.action)};
            }
        }
    }

   private:
    using LevelOrders = std::vector<Order>;
    struct PriceAndSide {
        int64_t price;
        Side side;
    };
    using Orders = std::unordered_map<uint64_t, PriceAndSide>;
    using SideLevels = std::map<int64_t, LevelOrders>;

    static PriceLevel GetPriceLevel(int64_t price, const LevelOrders level) {
        PriceLevel res{price};
        for (const auto& order : level) {
            if (!order.is_tob) {
                ++res.count;
            }
            res.size += order.size;
        }
        return res;
    }

    static LevelOrders::iterator GetLevelOrder(LevelOrders& level, uint64_t order_id) {
        auto order_it = std::find_if(level.begin(), level.end(), [order_id](const Order& order) {
            return order.id == order_id;
        });
        if (order_it == level.end()) {
            throw std::invalid_argument{"No order with ID " + std::to_string(order_id)};
        }
        return order_it;
    }

    void Clear() {
        orders_by_id_.clear();
        offers_.clear();
        bids_.clear();
    }

    void Add(UnixNanos ts_event, Side side, uint64_t order_id, int64_t price, uint32_t size,
             FlagSet flags) {
        const Order order{order_id, ts_event, price, size, side, flags.IsTob()};
        if (order.is_tob) {
            SideLevels& levels = GetSideLevels(side);
            levels.clear();
            LevelOrders level = {order};
            levels.emplace(price, level);
        } else {
            LevelOrders& level = GetOrInsertLevel(side, price);
            level.emplace_back(order);
            auto res = orders_by_id_.emplace(order_id, PriceAndSide{price, side});
            if (!res.second) {
                throw std::invalid_argument{"Received duplicated order ID " +
                                            std::to_string(order_id)};
            }
        }
    }

    void Cancel(Side side, uint64_t order_id, int64_t price, uint32_t size) {
        LevelOrders& level = GetLevel(side, price);
        auto order_it = GetLevelOrder(level, order_id);
        if (order_it->size < size) {
            throw std::logic_error{"Tried to cancel more size than existed for order ID " +
                                   std::to_string(order_id)};
        }
        order_it->size -= size;
        if (order_it->size == 0) {
            orders_by_id_.erase(order_id);
            level.erase(order_it);
            if (level.empty()) {
                RemoveLevel(side, price);
            }
        }
    }

    void Modify(UnixNanos ts_event, Side side, uint64_t order_id, int64_t price, uint32_t size,
                FlagSet flags) {
        auto price_side_it = orders_by_id_.find(order_id);
        if (price_side_it == orders_by_id_.end()) {
            // If order not found, treat it as an add
            Add(ts_event, side, order_id, price, size, flags);
            return;
        }
        if (price_side_it->second.side != side) {
            throw std::logic_error{"Order " + std::to_string(order_id) + " changed side"};
        }
        auto prev_price = price_side_it->second.price;
        auto& prev_level = GetLevel(side, prev_price);
        auto level_order_it = GetLevelOrder(prev_level, order_id);
        if (prev_price != price) {
            price_side_it->second.price = price;
            // Move to new price level
            Order order = *level_order_it;
            prev_level.erase(level_order_it);
            if (prev_level.empty()) {
                RemoveLevel(side, prev_price);
            }
            auto& level = GetOrInsertLevel(side, price);
            level.emplace_back(order);
            // Update order iterator
            level_order_it = std::prev(level.end());
            level_order_it->price = price;
            // Changing price loses priority
            level_order_it->ts_event = ts_event;
        } else if (level_order_it->size < size) {
            LevelOrders& level = prev_level;
            // Increasing size loses priority
            Order order = *level_order_it;
            level.erase(level_order_it);
            level.emplace_back(order);
            level_order_it = std::prev(level.end());
            level_order_it->ts_event = ts_event;
        }
        level_order_it->size = size;
    }

    SideLevels& GetSideLevels(Side side) {
        switch (side) {
            case Side::Ask: {
                return offers_;
            }
            case Side::Bid: {
                return bids_;
            }
            case Side::None:
            default: {
                throw std::invalid_argument{"Invalid side"};
            }
        }
    }

    LevelOrders& GetLevel(Side side, int64_t price) {
        SideLevels& levels = GetSideLevels(side);
        auto level_it = levels.find(price);
        if (level_it == levels.end()) {
            throw std::invalid_argument{std::string{"Received event for unknown level "} +
                                        ToString(side) + " " + PxToString(price)};
        }
        return level_it->second;
    }

    LevelOrders& GetOrInsertLevel(Side side, int64_t price) {
        SideLevels& levels = GetSideLevels(side);
        return levels[price];
    }

    void RemoveLevel(Side side, int64_t price) {
        SideLevels& levels = GetSideLevels(side);
        levels.erase(price);
    }

    Orders orders_by_id_;
    SideLevels offers_;
    SideLevels bids_;
};

class Market {
   public:
    struct PublisherBook {
        uint16_t publisher_id;
        Book book;
    };

    const std::vector<PublisherBook>& GetBooksByPub(uint32_t instrument_id) {
        return books_[instrument_id];
    }

    const Book& GetBook(uint32_t instrument_id, uint16_t publisher_id) {
        const auto& books = GetBooksByPub(instrument_id);
        auto book_it =
            std::find_if(books.begin(), books.end(), [publisher_id](const PublisherBook& pub_book) {
                return pub_book.publisher_id == publisher_id;
            });
        if (book_it == books.end()) {
            throw std::invalid_argument{"No book for publisher ID " + std::to_string(publisher_id)};
        }
        return book_it->book;
    }

    std::pair<PriceLevel, PriceLevel> Bbo(uint32_t instrument_id, uint16_t publisher_id) {
        const auto& book = GetBook(instrument_id, publisher_id);
        return book.Bbo();
    }

    std::pair<PriceLevel, PriceLevel> AggregatedBbo(uint32_t instrument_id) {
        PriceLevel agg_bid;
        PriceLevel agg_ask;
        for (const auto& pub_book : GetBooksByPub(instrument_id)) {
            const auto bbo = pub_book.book.Bbo();
            const auto& bid = bbo.first;
            const auto& ask = bbo.second;
            if (bid) {
                if (agg_bid.IsEmpty() || bid.price > agg_bid.price) {
                    agg_bid = bid;
                } else if (bid.price == agg_bid.price) {
                    agg_bid.count += bid.count;
                    agg_bid.size += bid.size;
                }
            }
            if (ask) {
                if (agg_ask.IsEmpty() || ask.price < agg_ask.price) {
                    agg_ask = ask;
                } else if (ask.price == agg_ask.price) {
                    agg_ask.count += ask.count;
                    agg_ask.size += ask.size;
                }
            }
        }
        return {agg_bid, agg_ask};
    }

    void Apply(const MboMsg& mbo_msg) {
        auto& instrument_books = books_[mbo_msg.hd.instrument_id];
        auto book_it = std::find_if(instrument_books.begin(), instrument_books.end(),
                                    [&mbo_msg](const PublisherBook& pub_book) {
                                        return pub_book.publisher_id == mbo_msg.hd.publisher_id;
                                    });
        if (book_it == instrument_books.end()) {
            instrument_books.emplace_back(PublisherBook{mbo_msg.hd.publisher_id, {}});
            book_it = std::prev(instrument_books.end());
        }
        book_it->book.Apply(mbo_msg);
    }

   private:
    std::unordered_map<uint32_t, std::vector<PublisherBook>> books_;
};

struct BookStateRow {
    long long timestamp;
    int orders;
    int quantity;
    float price;
    char side;
};

struct BentoDepthRow {
    long long timestamp;
    int command;
    int flag;
    int orders;
    float price;
    int quantity;
};

void print_bento_depth_row(const BentoDepthRow& row) {
    std::cout << "timestamp: " << row.timestamp << ", command: " << row.command
              << ", flag: " << row.flag << ", orders: " << row.orders << ", price: " << row.price
              << ", quantity: " << row.quantity << std::endl;
}

void print_book_state_row(const BookStateRow& row) {
    std::cout << "timestamp: " << row.timestamp << ", orders: " << row.orders
              << ", quantity: " << row.quantity << ", price: " << row.price
              << ", side: " << row.side << std::endl;
}

void add_book_state_row(std::vector<BookStateRow>& book_state, long long timestamp, int orders,
                        int quantity, float price, char side) {
    BookStateRow row;
    row.timestamp = timestamp;
    row.orders = orders;
    row.quantity = quantity;
    row.price = price;
    row.side = side;
    book_state.push_back(row);
}

void add_bento_depth_row(std::vector<BentoDepthRow>& bento_depth, long long timestamp, int command,
                         int flag, int orders, float price, int quantity) {
    BentoDepthRow row;
    row.timestamp = timestamp;
    row.command = command;
    row.flag = flag;
    row.orders = orders;
    row.price = price;
    row.quantity = quantity;
    bento_depth.push_back(row);
}

int main(int argc, const char** argv) {
    if (argc != 5) {
        std::cerr << "Usage: " << argv[0]
                  << " <input_file_path> <output_file_path> <snapshot_size> <n_states>"
                  << std::endl;
        return 1;
    }
    std::string input_file_path = argv[1];
    std::string output_file_path = argv[2];
    const int snapshot_size = std::stoi(argv[3]);
    const int n_states = std::stoi(argv[4]);

    int sierra_min_ns = 1000;
    float price_resolution = 1000000000.0f;

    bool init = true;
    long long counter = 0;
    long long prev_timestamp = 0;

    Market market;
    std::vector<BookStateRow> prev;
    std::vector<BentoDepthRow> bento_depth;

    auto record_callback = [&](const Record& record) {
        if (auto* mbo = record.GetIf<MboMsg>()) {
            market.Apply(*mbo);

            // if not last continue
            if (not mbo->flags.IsLast()) return KeepGoing::Continue;

            // if diff less than 1 ms continue (sierra depth is in ms)
            long long current_timestamp = mbo->hd.ts_event.time_since_epoch().count();
            auto diff = current_timestamp - prev_timestamp;
            prev_timestamp = current_timestamp;
            if (diff < sierra_min_ns) return KeepGoing::Continue;

            const auto& book = market.GetBook(mbo->hd.instrument_id, mbo->hd.publisher_id)
                                   .GetSnapshot(snapshot_size);

            std::vector<BookStateRow> book_state;
            for (const auto& ba_pair : book) {
                add_book_state_row(book_state, current_timestamp, ba_pair.bid_ct, ba_pair.bid_sz,
                                   ba_pair.bid_px / price_resolution, 'B');

                add_book_state_row(book_state, current_timestamp, ba_pair.ask_ct, ba_pair.ask_sz,
                                   ba_pair.ask_px / price_resolution, 'A');
            }

            if (init) {
                init = false;
                add_bento_depth_row(bento_depth, current_timestamp, 1, 0, 0, 0.0, 0);
                for (const auto& row : book_state) {
                    int command = row.side == 'B' ? 2 : 3;
                    add_bento_depth_row(bento_depth, row.timestamp, command, 0, row.orders,
                                        row.price, row.quantity);
                }
                prev = book_state;
                return KeepGoing::Continue;
            }

            // sets of prices for state diff algorithm
            std::set<float> prev_prices;
            for (const auto& row : prev) {
                prev_prices.insert(row.price);
            }
            std::set<float> current_prices;
            for (const auto& row : book_state) {
                current_prices.insert(row.price);
            }

            // dicts of price by BookStaterow for prev and current
            std::map<float, BookStateRow> prev_dict;
            for (const auto& row : prev) {
                prev_dict[row.price] = row;
            }
            std::map<float, BookStateRow> current_dict;
            for (const auto& row : book_state) {
                current_dict[row.price] = row;
            }

            // make deletes
            for (const auto& price : prev_prices) {
                auto& prev = prev_dict[price];
                if (current_prices.find(price) == current_prices.end()) {
                    int command = prev.side == 'B' ? 6 : 7;
                    add_bento_depth_row(bento_depth, current_timestamp, command, 1, 0, price, 0);
                }
            }

            // make all the rest
            for (const auto& price : current_prices) {
                auto& current = current_dict[price];
                auto& prev = prev_dict[price];
                // make add
                if (prev_prices.find(price) == prev_prices.end()) {
                    int command = current.side == 'B' ? 2 : 3;
                    add_bento_depth_row(bento_depth, current_timestamp, command, 1, current.orders,
                                        price, current.quantity);
                    continue;
                }
                if (current.side != prev.side) {
                    // make delete prev
                    int command = prev.side == 'B' ? 6 : 7;
                    add_bento_depth_row(bento_depth, current_timestamp, command, 1, 0, price, 0);
                    // make add current
                    command = current.side == 'B' ? 2 : 3;
                    add_bento_depth_row(bento_depth, current_timestamp, command, 1, current.orders,
                                        price, current.quantity);
                    continue;
                }
                if (current.orders != prev.orders or current.quantity != prev.quantity) {
                    // make modify
                    int command = current.side == 'B' ? 4 : 5;
                    add_bento_depth_row(bento_depth, current_timestamp, command, 1, current.orders,
                                        price, current.quantity);
                }
            }

            prev = book_state;

            counter++;
            if (counter % 100 == 0)
                std::cout << "[ " << ToIso8601(mbo->hd.ts_event) << " ] processed book states -> "
                          << counter << std::endl;

            if (n_states != -1 and counter >= n_states) return KeepGoing::Stop;
        }
        return KeepGoing::Continue;
    };

    auto file_store = DbnFileStore{input_file_path};
    file_store.Replay(record_callback);

    std::cout << "bento depth size: " << bento_depth.size() << std::endl;
    std::vector<std::string> header = {"timestamp", "command", "flag",
                                       "orders",    "price",   "quantity"};
    std::ofstream out_file(output_file_path);
    for (size_t i = 0; i < header.size() - 1; i++) {
        out_file << header[i] << ",";
    }
    out_file << header[header.size() - 1] << std::endl;

    out_file << std::endl;
    for (const auto& depth : bento_depth) {
        out_file << depth.timestamp << "," << depth.command << "," << depth.flag << ","
                 << depth.orders << "," << depth.price << "," << depth.quantity << std::endl;
    }
    out_file.close();
    std::cout << "done." << std::endl;
    return 0;
}
