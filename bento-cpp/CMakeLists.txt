cmake_minimum_required(VERSION 3.14)

project(databento_example)
include(FetchContent)

FetchContent_Declare(
  databento
  GIT_REPOSITORY https://github.com/databento/databento-cpp
  GIT_TAG HEAD
)
FetchContent_MakeAvailable(databento)

add_executable(example main.cpp)
target_link_libraries(example PRIVATE databento::databento)
