#include "PluginProcessor.h"
#include "PluginEditor.h"

LTAReelCaptureAudioProcessor::LTAReelCaptureAudioProcessor()
    : juce::AudioProcessor (BusesProperties()
        .withInput ("Input", juce::AudioChannelSet::stereo(), true)
        .withOutput ("Output", juce::AudioChannelSet::stereo(), true))
{
    diskThread.startThread();
}

LTAReelCaptureAudioProcessor::~LTAReelCaptureAudioProcessor()
{
    stopCapture();
    diskThread.stopThread (3000);
}

juce::File LTAReelCaptureAudioProcessor::captureFolder()
{
    auto folder = juce::File::getSpecialLocation (juce::File::userDocumentsDirectory)
                       .getChildFile ("LTA Reel Maker")
                       .getChildFile ("Captures");
    folder.createDirectory();
    return folder;
}

void LTAReelCaptureAudioProcessor::prepareToPlay (double sampleRate, int)
{
    captureSampleRate.store (sampleRate);
}

void LTAReelCaptureAudioProcessor::releaseResources()
{
    stopCapture();
}

bool LTAReelCaptureAudioProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    const auto& out = layouts.getMainOutputChannelSet();
    return (out == juce::AudioChannelSet::mono() || out == juce::AudioChannelSet::stereo())
        && layouts.getMainInputChannelSet() == out;
}

bool LTAReelCaptureAudioProcessor::startCapture()
{
    if (capturing.load()) return true;
    const auto sr = captureSampleRate.load();
    if (sr < 8000.0) return false;

    auto dir = captureFolder();
    if (! dir.isDirectory()) return false;
    const auto stamp = juce::Time::getCurrentTime().formatted ("%Y%m%d_%H%M%S");
    auto file = dir.getNonexistentChildFile ("Capture_" + stamp, ".wav", false);
    auto output = std::unique_ptr<juce::FileOutputStream> (file.createOutputStream());
    if (output == nullptr || !output->openedOk()) return false;

    juce::WavAudioFormat wave;
    // A 2-channel WAV is written even if the host uses mono (mono gets duplicated).
    std::unique_ptr<juce::AudioFormatWriter> formatWriter (
        wave.createWriterFor (output.release(), sr, 2, 24, {}, 0));
    if (formatWriter == nullptr) return false;

    // Buffered disk I/O: the audio thread writes to an internal FIFO, not the drive.
    auto newWriter = std::make_unique<juce::AudioFormatWriter::ThreadedWriter> (
        formatWriter.release(), diskThread, static_cast<int> (sr * 4));
    {
        const juce::SpinLock::ScopedLockType lock (writerLock);
        threadedWriter = std::move (newWriter);
    }
    currentFile = file;
    numSamples.store (0);
    hostBpm.store (0.0);
    capturing.store (true);
    return true;
}

void LTAReelCaptureAudioProcessor::stopCapture()
{
    if (! capturing.exchange (false)) return;
    std::unique_ptr<juce::AudioFormatWriter::ThreadedWriter> oldWriter;
    {
        const juce::SpinLock::ScopedLockType lock (writerLock);
        oldWriter = std::move (threadedWriter);
    }
    oldWriter.reset(); // write WAV header and flush the FIFO on the message thread

    // Minimal metadata beside the capture; master audio cannot supply exact channel MIDI.
    auto meta = currentFile.withFileExtension ("json");
    auto object = new juce::DynamicObject();
    object->setProperty ("origin", "LTA Reel Capture VST3 - master output");
    object->setProperty ("audio_file", currentFile.getFileName());
    object->setProperty ("sample_rate", captureSampleRate.load());
    object->setProperty ("duration_estimate", static_cast<double> (numSamples.load())
                            / juce::jmax (1.0, captureSampleRate.load()));
    object->setProperty ("bpm", hostBpm.load());
    object->setProperty ("note_data", "not available from master audio");
    meta.replaceWithText (juce::JSON::toString (juce::var (object), true));
}

void LTAReelCaptureAudioProcessor::processBlock (juce::AudioBuffer<float>& buffer,
                                                 juce::MidiBuffer&)
{
    juce::ScopedNoDenormals noDenormals;
    if (! capturing.load() || buffer.getNumChannels() == 0) return;
    if (auto* playhead = getPlayHead())
        if (auto pos = playhead->getPosition())
            if (auto bpm = pos->getBpm()) hostBpm.store (*bpm);

    const float* channels[2] = { buffer.getReadPointer (0),
                                  buffer.getReadPointer (juce::jmin (1, buffer.getNumChannels() - 1)) };
    const juce::SpinLock::ScopedTryLockType lock (writerLock);
    if (lock.isLocked() && threadedWriter != nullptr && capturing.load())
    {
        // write() enqueues audio in the background FIFO; return false means dropped data.
        if (threadedWriter->write (channels, buffer.getNumSamples()))
            numSamples.fetch_add (buffer.getNumSamples());
    }
    // Never alter the signal; plugin is a transparent recorder.
}

juce::AudioProcessorEditor* LTAReelCaptureAudioProcessor::createEditor()
{
    return new LTAReelCaptureAudioProcessorEditor (*this);
}
void LTAReelCaptureAudioProcessor::getStateInformation (juce::MemoryBlock& dest)
{
    const char bytes[] = "LTAReelCapture1";
    dest.append (bytes, sizeof (bytes));
}
void LTAReelCaptureAudioProcessor::setStateInformation (const void*, int)
{
    // Never resume capture automatically when reopening FL Studio projects.
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new LTAReelCaptureAudioProcessor();
}
