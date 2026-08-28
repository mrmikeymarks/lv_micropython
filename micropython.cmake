# Root native modules (appconfig, appkeys, appperf).
# Included via USER_C_MODULES; see docs/native-modules.md.

add_library(usermod_rootapp INTERFACE)

target_sources(usermod_rootapp INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/appconfig.c
    ${CMAKE_CURRENT_LIST_DIR}/appkeys.c
    ${CMAKE_CURRENT_LIST_DIR}/appperf.c
)

target_link_libraries(usermod INTERFACE usermod_rootapp)
