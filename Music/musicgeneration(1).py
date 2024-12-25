# -*- coding: utf-8 -*-
"""MusicGeneration.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1m7E42hVr5yzyEG4sWshVIJ4H_mY4TNYI
"""

!pip install muspy

!pip install music21

!pip install lilypond

!unzip /content/EMOPIA_1.0.zip

import os
from music21 import converter, instrument, note, chord
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
import torch
from torch.utils.data import Dataset, DataLoader
import random
import pandas as pd
import seaborn as sns

# Path to the EMOPIA dataset's MIDI files
filepath = "/content/EMOPIA_1.0/midis"
label_path = "/content/EMOPIA_1.0/label.csv"

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

"""### Data Exploration"""

# Load the label.csv file
labels_df = pd.read_csv(label_path, delimiter=",")
print("Columns in label.csv:", labels_df.columns)

# Extract unique IDs and their 4Q labels
labels_df = labels_df[["ID", "4Q"]]
labels_mapping = {
    1: "HVHA",
    2: "HVLA",
    3: "LVHA",
    4: "LVLA"
}
labels_df["4Q_label"] = labels_df["4Q"].map(labels_mapping)

# Convert to a dictionary mapping file IDs to 4Q labels
file_to_emotion = labels_df.set_index("ID")["4Q"].to_dict()
print("Label mapping loaded:", len(file_to_emotion))

labels_df.head()

"""We first make a list of all the songs as a music21 stream."""

def load_midi_files_with_emotions(filepath, file_to_emotion):
    midi_files = []
    file_emotions = []
    for file in os.listdir(filepath):
        if file.endswith(".mid"):
            file_id = file.split(".mid")[0]  # Extract file ID
            if file_id in file_to_emotion:  # Check if file has a label
                dir = os.path.join(filepath, file)
                midi = converter.parse(dir)
                midi_files.append(midi)
                file_emotions.append(file_to_emotion[file_id])
            else:
                print(f"Warning: No label found for file {file}")
    print(f"Total MIDI files loaded with labels: {len(midi_files)}")
    return midi_files, file_emotions

# Load MIDI files and their emotions
all_midis, emotions = load_midi_files_with_emotions(filepath, file_to_emotion)

"""Next, extracting components, in our case, piano chords and notes.

Note: building block
Chord: A group of notes
"""

def extract_notes(midi_files):
    notes = []
    for file in midi_files:
        songs = instrument.partitionByInstrument(file)
        for part in songs.parts:
            for element in part.recurse():
                if isinstance(element, note.Note):
                    notes.append(str(element.pitch))
                elif isinstance(element, chord.Chord):
                    notes.append(".".join(str(n) for n in element.normalOrder))
    return notes

Corpus = extract_notes(all_midis)
print("Total notes in all the midis in the dataset:", len(Corpus))

!pip install pretty_midi
!apt-get install -y fluidsynth

# Download FluidR3_GM.sf2 (a popular SoundFont)
!wget https://github.com/urish/pianolite/raw/main/soundfonts/FluidR3_GM.sf2

from IPython.display import Audio
import pretty_midi

# Path to the SoundFont (.sf2 file)
sf2_path = 'FluidR3_GM.sf2'  # Change to your SoundFont file path
midi_file = '/content/EMOPIA_1.0/midis/Q1_0vLPYiPN7qY_0.mid'  # Change to your MIDI file path

# Load the MIDI file
music = pretty_midi.PrettyMIDI(midi_file=midi_file)

# Convert the MIDI to a waveform using the SoundFont
waveform = music.fluidsynth(sf2_path=sf2_path)

# Display the waveform for playback
Audio(waveform, rate=44100)

# Count the frequency of each note
count_num = Counter(Corpus)
Recurrence = list(count_num.values())

#Exploring the notes dictionary
Notes = list(count_num.keys())
Recurrence = list(count_num.values())
#Average recurrenc for a note in Corpus
def Average(lst):
    return sum(lst) / len(lst)
print("Average recurrenc for a note in Corpus:", Average(Recurrence))
print("Most frequent note in Corpus appeared:", max(Recurrence), "times")
print("Least frequent note in Corpus appeared:", min(Recurrence), "time")

# Remove rare notes (frequency < 100)
rare_notes = [key for key, value in count_num.items() if value < 100]
Corpus = [note for note in Corpus if note not in rare_notes]
print("Length of Corpus after removing rare notes:", len(Corpus))

# Create mappings for notes to integers
symb = sorted(list(set(Corpus)))
mapping = {note: idx for idx, note in enumerate(symb)}
reverse_mapping = {idx: note for note, idx in mapping.items()}
vocab_size = len(symb)
print("Total notes in Corpus:", len(Corpus))
print("Unique notes:", vocab_size)

mapping

# Plot the frequency distribution
plt.figure(figsize=(18, 3), facecolor="#97BACB")
bins = np.arange(0, max(Recurrence), 50)
plt.hist(Recurrence, bins=bins, color="#97BACB")
plt.axvline(x=100, color="#DBACC1", label="Rare Note Threshold")
plt.title("Frequency Distribution of Notes in the Corpus")
plt.xlabel("Frequency of Notes")
plt.ylabel("Number of Notes")
plt.legend()
plt.show()

"""### Data Preprocessing

Now, we create a dictionary to map the notes to the indices or numbers. Then we encode and split the corpus into smaller sequences of equal length.
"""

def extract_sequences_with_emotions(midi_files, file_emotions, mapping, sequence_length=50):
    targets = []
    emotions = []

    for midi, emotion in zip(midi_files, file_emotions):
        notes = []

        # Extract notes and chords from the MIDI file using your existing extract_notes function
        notes = extract_notes([midi])

        # Create sequences of fixed length
        for i in range(0, len(notes) - sequence_length, sequence_length):
            sequence = notes[i:i + sequence_length]
            try:
                # Map the sequence of notes/chords to their corresponding indices
                targets.append([mapping[note] for note in sequence])
                emotions.append(emotion)  # Assign the same emotion to all sequences from this file
            except KeyError as e:
                print(f"KeyError: {e} - skipping this sequence")
                continue

    print(f"Total sequences extracted: {len(targets)}")
    print(f"Total emotions assigned: {len(emotions)}")
    return targets, emotions

# Extract sequences with their associated emotions
sequence_length = 50  # Define the length of each sequence
targets, emotions = extract_sequences_with_emotions(all_midis, emotions, mapping, sequence_length = 50)

targets

emotions

"""### Data Loading"""

len(targets)

len(emotions)

normalized_emotions = [label - 1 for label in emotions]  # Convert 1-based to 0-based

normalized_emotions

for seq in targets:
    assert len(seq) == sequence_length, "Inconsistent sequence length!"

class EmotionMusicDataset(Dataset):
    def __init__(self, targets, emotions):
        """
        Args:
            targets (list of lists): Target sequences of note indices.
            emotions (list): Emotion labels for each sequence.
        """
        self.targets = targets
        self.emotions = emotions

    def __len__(self):
        return len(self.targets)

    def __getitem__(self, idx):
        # Convert targets and emotions to tensors
        seq_out = torch.tensor(self.targets[idx]).long()
        emotion = torch.tensor(self.emotions[idx]).long()  # Numerical emotion
        return seq_out, emotion

from torch.utils.data import DataLoader

# Create dataset and dataloader
dataset = EmotionMusicDataset(targets, normalized_emotions)
dataloader = DataLoader(dataset, batch_size=16, shuffle=True, drop_last=True)

for batch in dataloader:
    sequences, labels = batch
    print(f"Sequences shape: {sequences.shape}, Labels shape: {labels.shape}")
    assert sequences.shape[0] == labels.shape[0], "Batch size mismatch!"

for seq_out, emotion in dataloader:
    # print("Input shape:", seq_in.shape)
    print("Target shape:", seq_out.shape)
    print("Emotion shape:", emotion.shape)
    break

# Check note mapping
print(mapping)

# Check emotion labels
print(emotion)  # Should be {0, 1, ..., num_emotions - 1}

print(seq_out)

"""### LSTM"""

import torch.nn as nn

# class EmotionMusicGenerationModel(nn.Module):
#     def __init__(self, vocab_size, embedding_dim, emotion_dim, hidden_dim=256, num_emotions=4, seq_len=50):
#         super(EmotionMusicGenerationModel, self).__init__()
#         self.emotion_embedding = nn.Embedding(num_emotions, emotion_dim)
#         self.note_embedding = nn.Embedding(vocab_size, embedding_dim)
#         self.lstm = nn.LSTM(embedding_dim + emotion_dim, hidden_dim, num_layers=2, batch_first=True)
#         self.fc = nn.Linear(hidden_dim, vocab_size)
#         self.seq_len = seq_len

#     def forward(self, emotion, input_sequence):
#         # Embed the emotion and input sequence
#         emotion_embedded = self.emotion_embedding(emotion)
#         embedded_sequence = self.note_embedding(input_sequence)

#         # Concatenate emotion embedding with note embeddings
#         lstm_input = torch.cat([embedded_sequence, emotion_embedded.unsqueeze(1).repeat(1, embedded_sequence.shape[1], 1)], dim=2)

#         # Pass through LSTM
#         output, _ = self.lstm(lstm_input)

#         # Predict next notes
#         output = self.fc(output)
#         return output

import torch.nn as nn

class EmotionMusicGenerationModel(nn.Module):
    def __init__(self, vocab_size, embedding_dim, emotion_dim, hidden_dim=256, num_emotions=4, seq_len=50, dropout_rate=0.3):
        super(EmotionMusicGenerationModel, self).__init__()
        self.emotion_embedding = nn.Embedding(num_emotions, emotion_dim)
        self.note_embedding = nn.Embedding(vocab_size, embedding_dim)
        self.lstm = nn.LSTM(embedding_dim + emotion_dim, hidden_dim, num_layers=2, batch_first=True, dropout=dropout_rate)  # Dropout in LSTM
        self.dropout = nn.Dropout(dropout_rate)  # Dropout layer after LSTM
        self.fc = nn.Linear(hidden_dim, vocab_size)
        self.seq_len = seq_len

    def forward(self, emotion, input_sequence):
        emotion_embedded = self.emotion_embedding(emotion)
        embedded_sequence = self.note_embedding(input_sequence)

        lstm_input = torch.cat([embedded_sequence, emotion_embedded.unsqueeze(1).repeat(1, embedded_sequence.shape[1], 1)], dim=2)

        output, _ = self.lstm(lstm_input)

        # Apply dropout after the LSTM:
        output = self.dropout(output)

        output = self.fc(output)
        return output

"""### Training"""

import torch.optim as optim

def train_model(model, data_loader, criterion, optimizer, num_epochs, device):
    model.to(device)
    model.train()

    for epoch in range(num_epochs):
        total_loss = 0.0

        for targets, emotions in data_loader:
            targets, emotions = targets.to(device), emotions.to(device)

            optimizer.zero_grad()

            # Pass both emotions and targets (input sequence) to the model
            outputs = model(emotions, targets)

            outputs = outputs.view(-1, outputs.size(-1))  # Reshape outputs for loss calculation
            targets = targets.view(-1)  # Reshape targets for loss calculation

            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        print(f"Epoch [{epoch + 1}/{num_epochs}], Loss: {total_loss / len(data_loader):.4f}")

    print("Training Complete")

def evaluate_model(model, data_loader, criterion, device):
    model.to(device)
    model.eval()

    total_loss = 0.0
    all_predictions = []
    all_targets = []

    with torch.no_grad():
        for targets, emotions in data_loader:
            targets, emotions = targets.to(device), emotions.to(device)

            # Pass both emotions and targets (input sequence) to the model
            outputs = model(emotions, targets)  # Changed line
            outputs = outputs.view(-1, outputs.size(-1))
            targets = targets.view(-1)

            loss = criterion(outputs, targets)
            total_loss += loss.item()

            predictions = torch.argmax(outputs, dim=1)
            all_predictions.extend(predictions.cpu().numpy())
            all_targets.extend(targets.cpu().numpy())

    accuracy = (np.array(all_predictions) == np.array(all_targets)).mean()
    print(f"Validation Loss: {total_loss / len(data_loader):.4f}, Accuracy: {accuracy * 100:.2f}%")

def generate_music(model, emotion_label, num_notes, mapping, device, temperature=1.0):
    model.to(device)
    model.eval()

    generated_sequence = []

    with torch.no_grad():
        emotion_tensor = torch.tensor([emotion_label], dtype=torch.long).to(device)

        # Initialize with a random note instead of zeros:
        initial_note = random.randint(0, len(mapping) - 1)  # Choose a random note index
        input_sequence = torch.tensor([[initial_note]], dtype=torch.long).to(device)

        for _ in range(num_notes):
            output = model(emotion_tensor, input_sequence)

            # Apply temperature for sampling diversity:
            output = output.squeeze(0) / temperature
            probabilities = torch.softmax(output, dim=0)
            predicted_note = torch.multinomial(probabilities, num_samples=1).item()

            try:
                predicted_note_str = reverse_mapping[predicted_note]
                generated_sequence.append(predicted_note_str)
            except KeyError:
                print(f"Warning: Predicted note index {predicted_note} is out of vocabulary. Replacing with default.")
                predicted_note_str = reverse_mapping[0]
                generated_sequence.append(predicted_note_str)

            input_sequence = torch.tensor([[predicted_note]], dtype=torch.long).to(device)

    return generated_sequence

# Model Parameters
vocab_size = len(mapping)  # Total number of unique notes
embedding_dim = 128  # Size of the note embeddings
emotion_dim = 64  # Size of the emotion embedding
hidden_dim = 256  # Number of hidden units in LSTM
num_emotions = len(set(emotions))  # Number of distinct emotions

# Instantiate Model
model = EmotionMusicGenerationModel(vocab_size=vocab_size,
                             embedding_dim=embedding_dim,
                             emotion_dim=emotion_dim,
                             hidden_dim=hidden_dim,
                             num_emotions=num_emotions)

# Define Loss and Optimizer
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

model

# Train the Model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
num_epochs = 50

print("Training the model...")
train_model(model, dataloader, criterion, optimizer, num_epochs, device)

# Commented out IPython magic to ensure Python compatibility.
# %load_ext tensorboard
# %tensorboard --logdir runs

# Save the model
torch.save(model.state_dict(), "emotion_music_model.pth")
print("Model saved.")

checkpoint = torch.load("emotion_music_model.pth")

# Load model weights
model.load_state_dict(checkpoint)

evaluate_model(model, dataloader, criterion, device)

notes = generate_music(model, emotion_label=3, num_notes=50, mapping=reverse_mapping, device=device, temperature=0.8)

notes

!pip install pretty_midi
!apt-get install -y fluidsynth

# Download FluidR3_GM.sf2 (a popular SoundFont)
!wget https://github.com/urish/pianolite/raw/main/soundfonts/FluidR3_GM.sf2

!apt-get update
!apt-get install -y fluidsynth

!wget https://github.com/musescore/MuseScore/raw/master/share/sound/MuseScore_General.sf3

import pretty_midi
from IPython.display import Audio

def notes_to_midi(notes, output_file, instrument_name='Acoustic Grand Piano'):
    midi = pretty_midi.PrettyMIDI()
    instrument_program = pretty_midi.instrument_name_to_program(instrument_name)
    instrument = pretty_midi.Instrument(program=instrument_program)

    # Assuming each note has a duration of 1 beat (adjust as needed)
    current_time = 0
    for note_name in notes:
        try:
            # Check if the note is a chord (contains '.')
            if '.' in note_name:
                # Handle chords separately
                chord_notes = note_name.split('.')
                for chord_note in chord_notes:
                    note_number = pretty_midi.note_name_to_number(chord_note)
                    # Check if note_number is within the valid range
                    note_number = max(0, min(note_number, 127))
                    note = pretty_midi.Note(velocity=100, pitch=note_number, start=current_time, end=current_time + 1)
                    instrument.notes.append(note)
            else:
                # Handle single notes
                note_number = pretty_midi.note_name_to_number(note_name)
                # Check if note_number is within the valid range
                note_number = max(0, min(note_number, 127))
                note = pretty_midi.Note(velocity=100, pitch=note_number, start=current_time, end=current_time + 1)
                instrument.notes.append(note)

            current_time += 1
        except Exception as e:
            print(f"Warning: Skipping invalid note '{note_name}': {e}")

    midi.instruments.append(instrument)
    midi.write(output_file)

def midi_to_wav(midi_file, wav_file, sf2_path='FluidR3_GM.sf2'):
    midi_data = pretty_midi.PrettyMIDI(midi_file)
    audio_data = midi_data.fluidsynth(sf2_path=sf2_path)
    Audio(audio_data, rate=44100).export(wav_file, format="wav")

notes = generate_music(model, emotion_label=2, num_notes=50, mapping=reverse_mapping, device=device, temperature=0.8)

notes

midi_file = 'generated_music.mid'
notes_to_midi(notes, midi_file)

# Convert MIDI to WAV
wav_file = 'generated_music.wav'
midi_to_wav(midi_file, wav_file)

# Play the WAV file in Colab
Audio(wav_file)
