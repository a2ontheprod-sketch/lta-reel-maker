#pragma once
#include <JuceHeader.h>
#include <atomic>
#include <memory>

class LTAReelCaptureAudioProcessor final : public juce::AudioProcessor
{
public:
    LTAReelCaptureAudioProcessor();
    ~LTAReelCaptureAudioProcessor() override;

    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    bool isBusesLayoutSupported (const BusesLayout&) const override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }
    const juce::String getName() const override { return "LTA Reel Capture"; }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0.0; }
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram (int) override {}
    const juce::String getProgramName (int) override { return "Default"; }
    void changeProgramName (int, const juce::String&) override {}
    void getStateInformation (juce::MemoryBlock&) override;
    void setStateInformation (const void*, int) override;

    bool startCapture();
    void stopCapture();
    bool isCapturing() const noexcept { return capturing.load(); }
    int64_t samplesCaptured() const noexcept { return numSamples.load(); }
    double getCaptureSampleRate() const noexcept { return captureSampleRate.load(); }
    juce::File getCaptureFile() const { return currentFile; }
    static juce::File captureFolder();

private:
    juce::TimeSliceThread diskThread { "LTA Reel Capture Disk Writer" };
    juce::SpinLock writerLock;
    std::unique_ptr<juce::AudioFormatWriter::ThreadedWriter> threadedWriter;
    std::atomic<bool> capturing { false };
    std::atomic<int64_t> numSamples { 0 };
    std::atomic<double> captureSampleRate { 44100.0 };
    std::atomic<double> hostBpm { 0.0 };
    juce::File currentFile;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (LTAReelCaptureAudioProcessor)
};
