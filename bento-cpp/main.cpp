#include <algorithm>
#include <cstdint>
#include <databento/constants.hpp>  // dataset, kUndefPrice
#include <databento/datetime.hpp>   // ToIso8601, UnixNanos
#include <databento/dbn_file_store.hpp>
#include <databento/enums.hpp>        // Action, Side
#include <databento/fixed_price.hpp>  // PxToString
#include <databento/flag_set.hpp>
#include <databento/historical.hpp>  // HistoricalBuilder
#include <databento/record.hpp>      // BidAskPair, MboMsg, Record
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <stdexcept>
#include <string>
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
    stream << level.size << " @ " << PxToString(level.price) << " | "
           << level.count << " order(s)";
    return stream;
}

class Book {
   public:
    std::pair<PriceLevel, PriceLevel> Bbo() const {
        return {GetBidLevel(), GetAskLevel()};
    }

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
                Add(mbo_msg.hd.ts_event, mbo_msg.side, mbo_msg.order_id,
                    mbo_msg.price, mbo_msg.size, mbo_msg.flags);
                break;
            }
            case Action::Cancel: {
                Cancel(mbo_msg.side, mbo_msg.order_id, mbo_msg.price,
                       mbo_msg.size);
                break;
            }
            case Action::Modify: {
                Modify(mbo_msg.hd.ts_event, mbo_msg.side, mbo_msg.order_id,
                       mbo_msg.price, mbo_msg.size, mbo_msg.flags);
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

    static LevelOrders::iterator GetLevelOrder(LevelOrders& level,
                                               uint64_t order_id) {
        auto order_it = std::find_if(
            level.begin(), level.end(),
            [order_id](const Order& order) { return order.id == order_id; });
        if (order_it == level.end()) {
            throw std::invalid_argument{"No order with ID " +
                                        std::to_string(order_id)};
        }
        return order_it;
    }

    void Clear() {
        orders_by_id_.clear();
        offers_.clear();
        bids_.clear();
    }

    void Add(UnixNanos ts_event, Side side, uint64_t order_id, int64_t price,
             uint32_t size, FlagSet flags) {
        const Order order{order_id, ts_event, price, size, side, flags.IsTob()};
        if (order.is_tob) {
            SideLevels& levels = GetSideLevels(side);
            levels.clear();
            LevelOrders level = {order};
            levels.emplace(price, level);
        } else {
            LevelOrders& level = GetOrInsertLevel(side, price);
            level.emplace_back(order);
            auto res =
                orders_by_id_.emplace(order_id, PriceAndSide{price, side});
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
            throw std::logic_error{
                "Tried to cancel more size than existed for order ID " +
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

    void Modify(UnixNanos ts_event, Side side, uint64_t order_id, int64_t price,
                uint32_t size, FlagSet flags) {
        auto price_side_it = orders_by_id_.find(order_id);
        if (price_side_it == orders_by_id_.end()) {
            // If order not found, treat it as an add
            Add(ts_event, side, order_id, price, size, flags);
            return;
        }
        if (price_side_it->second.side != side) {
            throw std::logic_error{"Order " + std::to_string(order_id) +
                                   " changed side"};
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
            throw std::invalid_argument{
                std::string{"Received event for unknown level "} +
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
            std::find_if(books.begin(), books.end(),
                         [publisher_id](const PublisherBook& pub_book) {
                             return pub_book.publisher_id == publisher_id;
                         });
        if (book_it == books.end()) {
            throw std::invalid_argument{"No book for publisher ID " +
                                        std::to_string(publisher_id)};
        }
        return book_it->book;
    }

    std::pair<PriceLevel, PriceLevel> Bbo(uint32_t instrument_id,
                                          uint16_t publisher_id) {
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
        auto book_it = std::find_if(
            instrument_books.begin(), instrument_books.end(),
            [&mbo_msg](const PublisherBook& pub_book) {
                return pub_book.publisher_id == mbo_msg.hd.publisher_id;
            });
        if (book_it == instrument_books.end()) {
            instrument_books.emplace_back(
                PublisherBook{mbo_msg.hd.publisher_id, {}});
            book_it = std::prev(instrument_books.end());
        }
        book_it->book.Apply(mbo_msg);
    }

   private:
    std::unordered_map<uint32_t, std::vector<PublisherBook>> books_;
};

struct BookRow {
    std::string timestamp;
    int orders;
    int quantity;
    float price;
    bool side;
};

struct BentoDepthRow {
    std::string timestamp;
    std::string command;
    int flag;
    int orders;
    float price;
    int quantity;
};

int main() {
    // First, create a historical client
    auto client =
        HistoricalBuilder{}.SetKey("db-bK9h5rwG4qSWNs4T4M4NCftDHDsYf").Build();

    // Next, we'll set up the books and book handlers
    Market market;
    // We'll parse symbology from the DBN metadata
    std::unordered_map<uint32_t, std::string> symbol_mappings;
    auto metadata_callback = [&symbol_mappings](Metadata metadata) {
        for (const auto& mapping : metadata.mappings) {
            symbol_mappings[std::stoi(mapping.intervals.at(0).symbol)] =
                mapping.raw_symbol;
        }
    };

    const int snapshot_size = 100;

    long counter = 0;

    auto record_callback = [&market, &symbol_mappings,
                            &counter](const Record& record) {
        if (auto* mbo = record.GetIf<MboMsg>()) {
            market.Apply(*mbo);

            if (mbo->flags.IsLast()) {
                const auto& symbol = symbol_mappings[mbo->hd.instrument_id];
                const auto& book =
                    market.GetBook(mbo->hd.instrument_id, mbo->hd.publisher_id)
                        .GetSnapshot(snapshot_size);

                auto timestamp = ToString(mbo->hd.ts_event);
                std::vector<BookRow> book_state;
                for (const auto& ba_pair : book) {
                    BookRow bid_row;
                    bid_row.timestamp = timestamp;
                    bid_row.orders = ba_pair.bid_ct;
                    bid_row.quantity = ba_pair.bid_sz;
                    bid_row.price = ba_pair.bid_px;
                    bid_row.side = 0;
                    book_state.push_back(bid_row);

                    BookRow ask_row;
                    ask_row.timestamp = timestamp;
                    ask_row.orders = ba_pair.ask_ct;
                    ask_row.quantity = ba_pair.ask_sz;
                    ask_row.price = ba_pair.ask_px;
                    ask_row.side = 1;
                    book_state.push_back(ask_row);
                }

                // delete me
                for (const auto& row : book_state) {
                    for (const auto& row : book_state) {
                        int inner = counter + 1;
                    }
                }
                for (const auto& row : book_state) {
                    for (const auto& row : book_state) {
                        int inner = counter + 1;
                    }
                }
                // delete me

                counter++;
                if (counter % 1000 == 0)
                    std::cout << "processed book states -> " << counter
                              << std::endl;
            }
        }
        return KeepGoing::Continue;
    };

    auto file_path =
        "/home/darchitect/work/phitech/bento-cpp/"
        "mes-bento-small.mbo.dbn.zst";
    auto file_store = DbnFileStore{file_path};
    file_store.Replay(metadata_callback, record_callback);
    return 0;
}
