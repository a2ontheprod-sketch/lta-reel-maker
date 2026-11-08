#include "PluginEditor.h"

LTAReelCaptureAudioProcessorEditor::LTAReelCaptureAudioProcessorEditor (LTAReelCaptureAudioProcessor& p)
    : juce::AudioProcessorEditor (&p), processor (p)
{
    setSize (480, 340);
    recordButton.setColour (juce::TextButton::buttonColourId, juce::Colour::fromRGB (249, 99, 164));
    recordButton.setColour (juce::TextButton::textColourOffId, juce::Colour::fromRGB (26, 14, 23));
    recordButton.onClick = [this]
    {
        if (processor.isCapturing()) processor.stopCapture();
        else if (! processor.startCapture())
            juce::AlertWindow::showMessageBoxAsync (juce::MessageBoxIconType::WarningIcon,
                                                     "LTA REEL CAPTURE", "Could not start WAV recording.");
        timerCallback();
    };
    addAndMakeVisible (recordButton);
    folderButton.setColour (juce::TextButton::buttonColourId, juce::Colour::fromRGB (39, 37, 49));
    folderButton.setColour (juce::TextButton::textColourOffId, juce::Colours::white);
    folderButton.onClick = [] { LTAReelCaptureAudioProcessor::captureFolder().revealToUser(); };
    addAndMakeVisible (folderButton);
    statusLabel.setJustificationType (juce::Justification::centred);
    statusLabel.setColour (juce::Label::textColourId, juce::Colour::fromRGB (188, 183, 204));
    addAndMakeVisible (statusLabel);
    startTimerHz (8);
    timerCallback();
}

void LTAReelCaptureAudioProcessorEditor::paint (juce::Graphics& g)
{
    const auto bg = juce::Colour::fromRGB (13, 13, 18);
    const auto pink = juce::Colour::fromRGB (250, 105, 169);
    g.fillAll (bg);
    g.setColour (juce::Colour::fromRGB (30, 29, 39));
    g.fillRoundedRectangle (16, 15, getWidth() - 32.0f, getHeight() - 30.0f, 20.0f);
    g.setColour (juce::Colours::white);
    g.setFont (juce::Font (juce::FontOptions (31.0f, juce::Font::bold)));
    g.drawText ("LTA", 34, 30, 115, 43, juce::Justification::centredLeft);
    g.setFont (juce::Font (juce::FontOptions (15.0f)));
    g.drawText ("REEL CAPTURE", 127, 40, 205, 28, juce::Justification::centredLeft);
    g.setColour (pink);
    g.drawEllipse (getWidth() * 0.5f - 60, 96, 120, 120, 4.0f);
    g.fillEllipse (getWidth() * 0.5f - 11, 145, 22, 22);
    g.setColour (juce::Colour::fromRGB (89, 82, 103));
    g.setFont (juce::Font (juce::FontOptions (11.0f)));
    g.drawText ("MASTER AUDIO • WAV CAPTURE", 20, getHeight() - 33, getWidth() - 40, 20,
                juce::Justification::centred);
}

void LTAReelCaptureAudioProcessorEditor::resized()
{
    recordButton.setBounds (getWidth() / 2 - 86, 228, 172, 40);
    folderButton.setBounds (getWidth() / 2 - 86, 277, 172, 27);
    statusLabel.setBounds (20, 194, getWidth() - 40, 28);
}

void LTAReelCaptureAudioProcessorEditor::timerCallback()
{
    const auto on = processor.isCapturing();
    recordButton.setButtonText (on ? "■  STOP" : "●  REC");
    if (on)
    {
        const auto duration = static_cast<double> (processor.samplesCaptured())
                              / juce::jmax (1.0, processor.getCaptureSampleRate());
        statusLabel.setText ("RECORDING  " + juce::String (duration, 1) + "s", juce::dontSendNotification);
    }
    else
    {
        statusLabel.setText ("READY • Capture to Documents/LTA Reel Maker", juce::dontSendNotification);
    }
}
