cmake_minimum_required(VERSION 3.22)
project(LTAReelMakerCapture VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)
FetchContent_Declare(JUCE
    GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
    GIT_TAG 8.0.10
    GIT_SHALLOW TRUE)
FetchContent_MakeAvailable(JUCE)

juce_add_plugin(LTAReelCapture
    COMPANY_NAME "LTA LABS"
    BUNDLE_ID "com.ltalabs.reelcapture"
    PLUGIN_MANUFACTURER_CODE LtaX
    PLUGIN_CODE RlC1
    FORMATS VST3
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT FALSE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS FALSE
    COPY_PLUGIN_AFTER_BUILD FALSE
    VST3_CATEGORIES Fx
    PRODUCT_NAME "LTA Reel Capture"
)

juce_generate_juce_header(LTAReelCapture)
target_sources(LTAReelCapture PRIVATE
    Source/PluginProcessor.h
    Source/PluginProcessor.cpp
    Source/PluginEditor.h
    Source/PluginEditor.cpp)
target_compile_definitions(LTAReelCapture PUBLIC
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0)
target_link_libraries(LTAReelCapture PRIVATE
    juce::juce_audio_utils
    juce::juce_gui_extra
    juce::juce_audio_formats
    juce::juce_dsp
    PUBLIC juce::juce_recommended_config_flags juce::juce_recommended_lto_flags
)
