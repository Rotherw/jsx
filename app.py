# -*- coding: utf-8 -*-
"""
Prosty generator obrazów (Stable Diffusion 1.5) z interfejsem w przeglądarce.

Model NIE jest ładowany przy starcie — interfejs otwiera się natychmiast.
Wagi modelu (~4 GB) pobierają się dopiero przy pierwszym kliknięciu
"Generuj" i trafiają do lokalnego cache Hugging Face, więc każde kolejne
uruchomienie korzysta już z dysku.
"""

import threading

import gradio as gr
import torch

MODEL_ID = "stable-diffusion-v1-5/stable-diffusion-v1-5"

_pipe = None
_pipe_lock = threading.Lock()


def _get_pipe():
    """Leniwie ładuje pipeline — przy pierwszym wywołaniu pobiera wagi (~4 GB)."""
    global _pipe
    with _pipe_lock:
        if _pipe is None:
            from diffusers import StableDiffusionPipeline

            cuda = torch.cuda.is_available()
            print(
                "Ładowanie modelu... "
                + ("(GPU: " + torch.cuda.get_device_name(0) + ")" if cuda else "(brak GPU — tryb CPU, będzie wolno)")
            )
            pipe = StableDiffusionPipeline.from_pretrained(
                MODEL_ID,
                torch_dtype=torch.float16 if cuda else torch.float32,
                safety_checker=None,
            )
            pipe = pipe.to("cuda" if cuda else "cpu")
            if cuda:
                pipe.enable_attention_slicing()
            _pipe = pipe
    return _pipe


def generate(prompt, negative_prompt, steps, guidance, seed):
    if not prompt or not prompt.strip():
        raise gr.Error("Wpisz opis obrazu (prompt).")

    pipe = _get_pipe()

    generator = None
    if seed is not None and int(seed) >= 0:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        generator = torch.Generator(device=device).manual_seed(int(seed))

    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt or None,
        num_inference_steps=int(steps),
        guidance_scale=float(guidance),
        generator=generator,
    )
    return result.images[0]


with gr.Blocks(title="Generator obrazów") as demo:
    gr.Markdown(
        "# Generator obrazów (Stable Diffusion 1.5)\n"
        "Przy **pierwszym** generowaniu pobiorą się wagi modelu (~4 GB) — to zajmie chwilę. "
        "Postęp pobierania widać w oknie konsoli."
    )
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="Prompt (opis obrazu)", lines=3, placeholder="np. a cat astronaut, digital art")
            negative = gr.Textbox(label="Negative prompt (czego unikać)", lines=2)
            steps = gr.Slider(1, 50, value=25, step=1, label="Kroki (steps)")
            guidance = gr.Slider(1.0, 15.0, value=7.5, step=0.5, label="Guidance scale")
            seed = gr.Number(value=-1, precision=0, label="Seed (-1 = losowy)")
            btn = gr.Button("Generuj", variant="primary")
        with gr.Column():
            output = gr.Image(label="Wynik", type="pil")

    btn.click(generate, inputs=[prompt, negative, steps, guidance, seed], outputs=output)


if __name__ == "__main__":
    # inbrowser=True — od razu otwiera interfejs w oknie przeglądarki
    demo.launch(inbrowser=True)
