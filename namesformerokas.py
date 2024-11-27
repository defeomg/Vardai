# -*- coding: utf-8 -*-
"""NamesformeRokas.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/130Nmc5FzLrwPz8vK4UYVpPlJ7I7zqz6Y
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader, Dataset
from torch.nn.utils.rnn import pad_sequence
import requests
from bs4 import BeautifulSoup

# Reusable function for scraping names by gender
def scrape_names(gender):
    base_url = "https://vardai.vlkk.lt/sarasas/"
    keys = ['a', 'b', 'c', 'c-2', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',
            'm', 'n', 'o', 'p', 'r', 's', 's-2', 't', 'u', 'v', 'z', 'z-2']
    names = []
    gender_class = "names_list__links--man" if gender == "male" else "names_list__links--woman"

    for key in keys:
        url = f"{base_url}{key}/"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', class_=f'names_list__links {gender_class}')
        names += [name.text for name in links]
    return names

# Scraping Male Names
male_names = scrape_names("male")
np.savetxt('male_names.txt', male_names, fmt='%s', header='name', comments='', newline='\n')

# Scraping Female Names
female_names = scrape_names("female")
np.savetxt('female_names.txt', female_names, fmt='%s', header='name', comments='', newline='\n')

class NameDataset(Dataset):
    def __init__(self, csv_file):
        self.names = pd.read_csv(csv_file, skiprows=1, header=None)[0].values
        self.chars = sorted(list(set(''.join(self.names) + ' ')))  # Include padding character
        self.char_to_int = {c: i for i, c in enumerate(self.chars)}
        self.int_to_char = {i: c for c, i in self.char_to_int.items()}
        self.vocab_size = len(self.chars)

    def __len__(self):
        return len(self.names)

    def __getitem__(self, idx):
        name = self.names[idx] + ' '  # Add padding character at the end
        encoded_name = [self.char_to_int[char] for char in name]
        return torch.tensor(encoded_name)

# Positional Encoding
def positional_encoding(seq_len, embed_dim):
    position = torch.arange(seq_len).unsqueeze(1)
    div_term = torch.exp(torch.arange(0, embed_dim, 2) * -(torch.log(torch.tensor(10000.0)) / embed_dim))
    pe = torch.zeros(seq_len, embed_dim)
    pe[:, 0::2] = torch.sin(position * div_term)
    pe[:, 1::2] = torch.cos(position * div_term)
    return pe.unsqueeze(0)

# Custom Collate Function for Padding
def pad_collate(batch):
    padded_seqs = pad_sequence(batch, batch_first=True, padding_value=0)
    input_seq = padded_seqs[:, :-1]
    target_seq = padded_seqs[:, 1:]
    return input_seq, target_seq

class MinimalTransformer(nn.Module):
    def __init__(self, vocab_size, embed_size, num_heads):
        super(MinimalTransformer, self).__init__()
        self.embed = nn.Embedding(vocab_size, embed_size)
        self.positional_encoding = nn.Parameter(positional_encoding(100, embed_size))
        self.encoder_layer = nn.TransformerEncoderLayer(d_model=embed_size, nhead=num_heads)
        self.transformer_encoder = nn.TransformerEncoder(self.encoder_layer, num_layers=1)
        self.output_layer = nn.Linear(embed_size, vocab_size)

    def forward(self, x):
        x = self.embed(x) + self.positional_encoding[:, :x.size(1), :]
        x = self.transformer_encoder(x)
        x = self.output_layer(x)
        return x

def train_model(model, dataloader, epochs=10):
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters())

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0

        for input_seq, target_seq in dataloader:
            optimizer.zero_grad()
            output = model(input_seq)
            loss = criterion(output.transpose(1, 2), target_seq)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        average_loss = total_loss / len(dataloader)
        print(f"Epoch {epoch+1}, Average Loss: {average_loss}")

def sample_with_temperature(model, dataset, start_str='a', max_length=20, k=5, temperature=1.0):
    assert temperature > 0, "Temperature must be greater than 0"
    model.eval()
    with torch.no_grad():
        input_seq = torch.tensor([dataset.char_to_int[c] for c in start_str]).unsqueeze(0)
        output_name = start_str
        for _ in range(max_length - len(start_str)):
            output = model(input_seq)
            logits = output[0, -1] / temperature
            top_k_probs, top_k_indices = torch.topk(torch.softmax(logits, dim=0), k)
            next_char_idx = top_k_indices[torch.multinomial(top_k_probs, 1).item()].item()
            next_char = dataset.int_to_char[next_char_idx]
            if next_char == ' ':
                break
            output_name += next_char
            input_seq = torch.cat([input_seq, torch.tensor([[next_char_idx]])], dim=1)
        return output_name

# Constants
BATCH_SIZE = 32
EMBED_SIZE = 128
NUM_HEADS = 8
EPOCHS = 10

# Male Names Model
male_dataset = NameDataset('male_names.txt')
male_dataloader = DataLoader(male_dataset, batch_size=BATCH_SIZE, shuffle=True, collate_fn=pad_collate)
male_model = MinimalTransformer(vocab_size=male_dataset.vocab_size, embed_size=EMBED_SIZE, num_heads=NUM_HEADS)
print("\nTraining Male Names Model:")
train_model(male_model, male_dataloader, epochs=EPOCHS)

# Save the male model
torch.save(male_model.state_dict(), 'male_model.pth')  # Save the model to a file
print("Male model saved to 'male_model.pth'.")

# Female Names Model
female_dataset = NameDataset('female_names.txt')
female_dataloader = DataLoader(female_dataset, batch_size=BATCH_SIZE, shuffle=True, collate_fn=pad_collate)
female_model = MinimalTransformer(vocab_size=female_dataset.vocab_size, embed_size=EMBED_SIZE, num_heads=NUM_HEADS)
print("\nTraining Female Names Model:")
train_model(female_model, female_dataloader, epochs=EPOCHS)

# Save the female model
torch.save(female_model.state_dict(), 'female_model.pth')  # Save the model to a file
print("Female model saved to 'female_model.pth'.")

# Generating Names
print("\nGenerated Male Names:")
for _ in range(10):
    print(' ', sample_with_temperature(male_model, male_dataset, start_str='J', k=5, temperature=0.5))

print("\nGenerated Female Names:")
for _ in range(10):
    print(' ', sample_with_temperature(female_model, female_dataset, start_str='A', k=5, temperature=1.5))