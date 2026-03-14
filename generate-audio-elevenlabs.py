#!/usr/bin/env python3
"""
Generate dramatic audio clips using ElevenLabs TTS API.

For the ~10 most dramatic moments during the eclipse, ElevenLabs
provides more expressive, emotionally compelling delivery than edge-tts.

Usage:
    pip install elevenlabs
    export ELEVENLABS_API_KEY="your-key-here"
    python3 generate-audio-elevenlabs.py

The generated clips are saved alongside edge-tts clips in audio/{en,es}/
and will be picked up by inject-audio.py. They OVERWRITE the edge-tts
versions for dramatic events only.

Note: ElevenLabs free tier allows ~10,000 chars/month.
This script generates ~15 dramatic clips × 2 languages ≈ ~8,000 chars.
"""

import os
import sys
from pathlib import Path

try:
    from elevenlabs import ElevenLabs
except ImportError:
    print("elevenlabs not installed. Run: pip install elevenlabs")
    print("Then set: export ELEVENLABS_API_KEY='your-key-here'")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not API_KEY:
    print("Set ELEVENLABS_API_KEY environment variable")
    print("  export ELEVENLABS_API_KEY='your-key-here'")
    sys.exit(1)

# ElevenLabs voices — pick expressive, dramatic voices
# Browse voices at: https://elevenlabs.io/voice-library
VOICES = {
    "en": {
        "voice_id": "pNInz6obpgDQGcFmaJgB",  # "Adam" — deep, dramatic male
        "model_id": "eleven_multilingual_v2",
    },
    "es": {
        "voice_id": "pNInz6obpgDQGcFmaJgB",  # Same voice, multilingual model handles Spanish
        "model_id": "eleven_multilingual_v2",
    },
}

# Only generate these dramatic clips with ElevenLabs
# (the rest use edge-tts which is free and unlimited)
DRAMATIC_CLIPS = {
    "en": {
        "dark_shadow_approaching": "Turn to the west-northwest. See that darkness on the horizon? That is the Moon's shadow — racing toward us at fifteen hundred kilometers per hour across the Atlantic. It's coming. And it has your name on it.",
        "diamond_ring_pre": "DIAMOND RING! The last sliver of the Sun blazes like a jewel against the corona! Ten seconds to totality!",
        "bailys_beads_pre": "Baily's Beads! Beads of sunlight streaming through the Moon's valleys! Glasses off in five — four — three — two — one —",
        "c2_totality": "TOTALITY! GLASSES OFF! The Sun is GONE! Day has become NIGHT over León! Look at it! LOOK AT IT!",
        "chromosphere": "The chromosphere! That thin pink-red ring on the Moon's edge — the Sun's lower atmosphere, normally invisible! And look — prominences! Red loops of plasma! Solar maximum is delivering!",
        "corona_full": "The corona in all its glory. White streamers extending millions of kilometers in every direction. Venus blazes to the southwest. You are standing inside a three hundred sixty degree sunset.",
        "maximum_eclipse": "MAXIMUM ECLIPSE! Twenty-nine minutes and eighteen seconds past eight. The Moon is perfectly centered on the Sun. Magnitude one point zero one zero. Savor this — forty-six seconds remain.",
        "totality_warning": "Thirty seconds of totality left. Take it all in. The corona. The horizon glow. The stars. Lock this into your memory. You'll carry it the rest of your life.",
        "chromosphere_returns": "Five seconds! The chromosphere is flashing on the trailing edge! Get your glasses ready — GLASSES BACK ON!",
        "c3_totality_ends": "THIRD CONTACT! GLASSES ON — NOW! Totality is OVER! One minute and thirty-two seconds of pure magic. The diamond ring blazes on the far side!",
    },
    "es": {
        "dark_shadow_approaching": "Girad hacia el oeste-noroeste. ¿Veis esa oscuridad en el horizonte? Esa es la sombra de la Luna — corriendo hacia nosotros a mil quinientos kilómetros por hora cruzando el Atlántico. Viene. Y tiene vuestro nombre.",
        "diamond_ring_pre": "¡ANILLO DE DIAMANTE! ¡El último trozo de Sol brilla como una joya contra la corona! ¡Diez segundos para la totalidad!",
        "bailys_beads_pre": "¡Perlas de Baily! ¡Puntos de luz a través de los valles de la Luna! Filtros fuera en cinco — cuatro — tres — dos — uno —",
        "c2_totality": "¡TOTALIDAD! ¡FILTROS FUERA! ¡El Sol ha DESAPARECIDO! ¡El día se ha convertido en NOCHE sobre León! ¡Mirad! ¡MIRAD!",
        "chromosphere": "¡La cromosfera! Ese fino anillo rosa-rojo en el borde de la Luna — la atmósfera inferior del Sol, ¡normalmente invisible! ¡Y mirad — prominencias! ¡Lazos rojos de plasma! ¡El máximo solar cumple!",
        "corona_full": "La corona en toda su gloria. Chorros blancos extendiéndose millones de kilómetros en todas direcciones. Venus brilla al suroeste. Estáis dentro de un atardecer de trescientos sesenta grados.",
        "maximum_eclipse": "¡ECLIPSE MÁXIMO! Las veinte horas, veintinueve minutos y dieciocho segundos. La Luna perfectamente centrada en el Sol. Magnitud uno coma cero uno cero. Saboread esto — quedan cuarenta y seis segundos.",
        "totality_warning": "Treinta segundos de totalidad. Absorbed todo. La corona. El resplandor del horizonte. Las estrellas. Grabadlo en vuestra memoria. Lo llevaréis el resto de vuestras vidas.",
        "chromosphere_returns": "¡Cinco segundos! ¡La cromosfera brilla en el borde trasero! ¡Preparad los filtros — FILTROS PUESTOS!",
        "c3_totality_ends": "¡TERCER CONTACTO! ¡FILTROS PUESTOS — YA! ¡La totalidad ha TERMINADO! Un minuto y treinta y dos segundos de pura magia. ¡El anillo de diamante brilla en el otro lado!",
    },
}

OUTPUT_DIR = Path("audio")

# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_all():
    client = ElevenLabs(api_key=API_KEY)
    
    total = 0
    errors = []
    chars_used = 0
    
    for lang, clips in DRAMATIC_CLIPS.items():
        voice_config = VOICES[lang]
        print(f"\n{'='*60}")
        print(f"Generating {lang.upper()} dramatic clips (ElevenLabs)")
        print(f"Voice: {voice_config['voice_id']}, Model: {voice_config['model_id']}")
        print(f"{'='*60}")
        
        for clip_id, text in clips.items():
            output_path = OUTPUT_DIR / lang / f"{clip_id}.mp3"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Back up edge-tts version if it exists
            if output_path.exists():
                backup = output_path.with_suffix(".edge-tts.mp3")
                if not backup.exists():
                    output_path.rename(backup)
                    print(f"  · Backed up edge-tts version → {backup.name}")
            
            try:
                audio = client.text_to_speech.convert(
                    voice_id=voice_config["voice_id"],
                    model_id=voice_config["model_id"],
                    text=text,
                )
                
                # audio is a generator of bytes
                audio_bytes = b"".join(audio)
                output_path.write_bytes(audio_bytes)
                
                size_kb = len(audio_bytes) / 1024
                chars_used += len(text)
                print(f"  ✓ {lang}/{clip_id}.mp3 ({size_kb:.0f} KB, {len(text)} chars)")
                total += 1
                
            except Exception as e:
                print(f"  ✗ {lang}/{clip_id}: {e}")
                errors.append(f"{lang}/{clip_id}")
                # Restore edge-tts backup if generation failed
                backup = output_path.with_suffix(".edge-tts.mp3")
                if backup.exists() and not output_path.exists():
                    backup.rename(output_path)
    
    print(f"\n{'='*60}")
    print(f"✓ Generated {total} dramatic clips")
    print(f"  Characters used: {chars_used:,}")
    if errors:
        print(f"  ⚠ {len(errors)} failed: {', '.join(errors)}")
    print(f"\nNext: Run inject-audio.py to embed into eclipse.html")


if __name__ == "__main__":
    generate_all()
