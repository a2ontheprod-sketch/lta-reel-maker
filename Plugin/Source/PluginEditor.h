#pragma once
#include "PluginProcessor.h"

class LTAReelCaptureAudioProcessorEditor final : public juce::AudioProcessorEditor,
                                                 private juce::Timer
{
public:
    explicit LTAReelCaptureAudioProcessorEditor (LTAReelCaptureAudioProcessor&);
    ~LTAReelCaptureAudioProcessorEditor() override = default;
    void paint (juce::Graphics&) override;
    void resized() override;
private:
    void timerCallback() override;
    LTAReelCaptureAudioProcessor& processor;
    juce::TextButton recordButton { "●  REC" };
    juce::TextButton folderButton { "OPEN CAPTURES" };
    juce::Label statusLabel;
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (LTAReelCaptureAudioProcessorEditor)
};
