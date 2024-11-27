# -*- coding: utf-8 -*-
"""App.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1ios-Pjl0BfjE8SRvJQw6R7V2__3WrYeZ
"""
import streamlit as st
import torch
from namesformerokas import NameDataset, MinimalTransformer, sample_with_temperature
import random

# 1. Load datasets
male_dataset = NameDataset('male_names.txt')
female_dataset = NameDataset('female_names.txt')

# 2. Load pre-trained models
male_model = MinimalTransformer(vocab_size=male_dataset.vocab_size, embed_size=128, num_heads=8)
male_model.load_state_dict(torch.load('male_model.pth'))
male_model.eval()

female_model = MinimalTransformer(vocab_size=female_dataset.vocab_size, embed_size=128, num_heads=8)
female_model.load_state_dict(torch.load('female_model.pth'))
female_model.eval()

# 3. Streamlit UI
st.title("🎉 Vardų Generatorius")
st.write("Sukurkite unikalius vardus naudodami dirbtinio intelekto modelį!")

# 4. Gender Selection
gender = st.radio("Pasirinkite vardų tipą:", ["Vyriški vardai", "Moteriški vardai"])
model = male_model if gender == "Vyriški vardai" else female_model
dataset = male_dataset if gender == "Vyriški vardai" else female_dataset

# 5. Input Controls
start_str = st.text_input(
    "Įveskite pradžios raides (iki 5):",
    value="",
    max_chars=5,
    help="Nurodykite vardo pradžios raides (1–5 simboliai). Jei laukelis tuščias, sugeneruojamas atsitiktinis vardas."
)

# Random name generation if input is empty
if len(start_str) == 0:
    start_str = random.choice(dataset.chars)

temperature = st.slider(
    "Kūrybingumo lygis (temperatūra):",
    min_value=0.1,
    max_value=2.0,
    value=1.0,
    help="Mažesnė temperatūra suteikia tikslesnius rezultatus, didesnė – kūrybiškesnius."
)

# 6. Generate Names
if st.button("Generuoti vardus"):
    st.write(f"Sugeneruoti vardai, pradedant nuo: **{start_str}**")

    try:
        # Generate the most probable name
        output = model(torch.tensor([[dataset.char_to_int[c] for c in start_str]]))
        most_probable_char_idx = torch.argmax(output[0, -1]).item()
        most_probable_name = start_str + dataset.int_to_char[most_probable_char_idx]
        st.markdown(f"### Pagrindinis vardas: **{most_probable_name}**")

        # Generate other similar names
        st.markdown("#### Panašūs vardai:")
        for _ in range(5):  # Generate 5 similar names
            name = sample_with_temperature(
                model,
                dataset,
                start_str=start_str,
                max_length=10,  # Fixed length
                k=5,  # Fixed Top-k
                temperature=temperature,
            )
            st.write(f"- {name}")

    except Exception as e:
        st.error(f"Klaida generuojant vardus: {e}")


