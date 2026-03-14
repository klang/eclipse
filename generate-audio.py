#!/usr/bin/env python3
"""
Generate TTS audio clips for the Eclipse Commentator SPA.

Uses edge-tts (Microsoft Edge's free TTS API) to generate MP3 clips
for all 36 events in both English and Spanish, then encodes them as
base64 and writes a JavaScript file that can be injected into eclipse.html.

Usage:
    pip install edge-tts
    python3 generate-audio.py

Output:
    audio/en/*.mp3          — English audio clips
    audio/es/*.mp3          — Spanish audio clips
    audio-clips.js          — JS file with AUDIO_CLIPS object (base64 data URIs)

The generated audio-clips.js can be injected into eclipse.html by replacing
the empty AUDIO_CLIPS object, or loaded via inject-audio.py.
"""

import asyncio
import base64
import json
import os
import sys
from pathlib import Path

try:
    import edge_tts
except ImportError:
    print("edge-tts not installed. Run: pip install edge-tts")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Voices — picked for clarity and natural delivery
VOICES = {
    "en": "en-US-AndrewMultilingualNeural",  # clear male narrator
    "es": "es-ES-AlvaroNeural",              # clear male narrator, Castilian Spanish
}

# Alternative voices (uncomment to switch):
# "en": "en-US-AriaNeural",           # female, expressive
# "es": "es-MX-DaliaNeural",          # female, Mexican Spanish

# Rate adjustment: slightly faster for excitement, slower for dramatic
RATE_NORMAL = "+5%"
RATE_DRAMATIC = "+0%"

OUTPUT_DIR = Path("audio")
JS_OUTPUT = Path("audio-clips.js")

# ---------------------------------------------------------------------------
# Commentary scripts — must match SCRIPTS in eclipse.html exactly
# ---------------------------------------------------------------------------

SCRIPTS = {
    "en": {
        "welcome": "Thirty minutes to first contact. Make sure you have your eclipse glasses ready. Find a clear view to the west-northwest — the Sun will be just ten degrees above the horizon at totality. The greatest show on Earth is about to begin.",
        "c1_first_contact": "And we are OFF! First contact — nineteen thirty-two. The Moon has arrived. Over the next fifty-six minutes, it will slowly devour the Sun. The greatest show on Earth has begun here in Antoñán del Valle.",
        "moon_bites": "Through your eclipse glasses, you can now see it — a tiny bite taken from the Sun's upper edge. The Moon is on the move.",
        "obscuration_20": "Twenty percent of the Sun's disk is now covered. Still feels like a normal August evening here in León. But that is about to change.",
        "temperature_drop": "Temperature is starting to drop. The Sun is losing its power. You might feel the first hints of a chill as the Moon blocks more and more energy from reaching us.",
        "sharp_shadows": "Check out the shadows on the ground. See how the edges are getting razor-sharp? That's because the Sun is becoming a thin crescent — a line source of light instead of a disk.",
        "sky_darkens": "The sky is noticeably darker now. Two-thirds of the Sun is gone. Look around — the colors of the landscape are draining away, turning grey and metallic. The light is all wrong.",
        "weather_changes": "Feel that? The air is changing. Temperature has dropped several degrees. You might notice a light breeze shifting direction as the Moon's shadow alters the atmosphere above us.",
        "light_colors": "Eighty percent covered. The light is otherworldly now — flat, grey, desaturated. Everything looks like a faded photograph. Your brain knows something is deeply wrong with this light.",
        "venus_appears": "Look to the southwest! Venus has just become visible to the naked eye. A brilliant jewel in the darkening sky. And we still have ten minutes to totality.",
        "nature_reacts": "Listen. The birds are going quiet. Some are heading to roost, confused by the premature twilight. Nocturnal insects are waking up. Nature is being fooled by the Moon.",
        "dark_shadow_approaching": "Turn to the west-northwest. See that darkness on the horizon? That is the Moon's shadow — racing toward us at fifteen hundred kilometers per hour across the Atlantic. It's coming. And it has your name on it.",
        "shadow_bands_pre": "Shadow bands! Look at any flat white surface — rippling waves of light and dark, like the bottom of a swimming pool. The atmosphere is bending the last thin slice of sunlight.",
        "corona_appears": "Twenty seconds! The corona — the Sun's outer atmosphere — is becoming visible around the Moon. A ghostly white ring. This is it, folks.",
        "shadow_sweeps_in": "The shadow is HERE! Fifteen seconds! Darkness is sweeping in from the west like a tidal wave across the plain!",
        "diamond_ring_pre": "DIAMOND RING! The last sliver of the Sun blazes like a jewel against the corona! Ten seconds to totality!",
        "bailys_beads_pre": "Baily's Beads! Beads of sunlight streaming through the Moon's valleys! Glasses off in five — four — three — two — one —",
        "c2_totality": "TOTALITY! GLASSES OFF! The Sun is GONE! Day has become NIGHT over León! Look at it! LOOK AT IT!",
        "chromosphere": "The chromosphere! That thin pink-red ring on the Moon's edge — the Sun's lower atmosphere, normally invisible! And look — prominences! Red loops of plasma! Solar maximum is delivering!",
        "corona_full": "The corona in all its glory. White streamers extending millions of kilometers in every direction. Venus blazes to the southwest. You are standing inside a three hundred sixty degree sunset.",
        "maximum_eclipse": "MAXIMUM ECLIPSE! Twenty-nine minutes and eighteen seconds past eight. The Moon is perfectly centered on the Sun. Magnitude one point zero one zero. Savor this — forty-six seconds remain.",
        "totality_warning": "Thirty seconds of totality left. Take it all in. The corona. The horizon glow. The stars. Lock this into your memory. You'll carry it the rest of your life.",
        "chromosphere_returns": "Five seconds! The chromosphere is flashing on the trailing edge! Get your glasses ready — GLASSES BACK ON!",
        "c3_totality_ends": "THIRD CONTACT! GLASSES ON — NOW! Totality is OVER! One minute and thirty-two seconds of pure magic. The diamond ring blazes on the far side!",
        "bailys_beads_post": "Baily's Beads again on the trailing edge. The Sun fights its way back through the Moon's valleys.",
        "diamond_ring_post": "The second Diamond Ring blazes into existence. A jewel of sunlight against the fading corona. Welcome back, Sun. We missed you.",
        "shadow_sweeps_out": "The shadow is racing away to the east. Look at it go — fifteen hundred kilometers per hour, heading for the Mediterranean.",
        "corona_fades": "The corona fades from view. You won't see it again until the next total eclipse. Treasure that memory.",
        "shadow_horizon_retreat": "The Moon's shadow retreats over the eastern horizon. You can still see it — a dark patch against the evening sky, getting smaller every second.",
        "nature_returns": "Nature is recovering. Birds are singing again. The world goes back to normal. But you? You will never be quite the same.",
        "light_returns": "Light and temperature climbing back to normal. But the Sun is getting low now — still partially eclipsed as it sinks toward the west.",
        "eclipse_sunset": "Here it comes — the eclipsed Sun meeting the sunset. A crescent Sun sinking into an orange horizon. This sight — this exact combination — will not happen again in León until the year twenty-one eighty.",
        "sunset": "The Sun sets — still wearing the Moon's shadow on its face. An eclipsed sunset. Extraordinary. The eclipse continues below the horizon, but for us, the show is over.",
        "c4_fourth_contact": "Fourth contact. Twenty-one twenty-two. The Moon has fully departed. One hour, forty-nine minutes, and thirty-two seconds of celestial theatre. What a privilege. Thank you for being here.",
    },
    "es": {
        "welcome": "Treinta minutos para el primer contacto. Aseguraos de tener los filtros solares preparados. Buscad una vista despejada hacia el oeste-noroeste — el Sol estará a solo diez grados sobre el horizonte durante la totalidad. El mayor espectáculo de la Tierra está a punto de comenzar.",
        "c1_first_contact": "¡Y ARRANCAMOS! Primer contacto — las diecinueve treinta y dos. La Luna ha llegado. Durante los próximos cincuenta y seis minutos, devorará lentamente al Sol. El mayor espectáculo de la Tierra ha comenzado aquí en Antoñán del Valle.",
        "moon_bites": "A través de los filtros solares, ya se ve — un pequeño mordisco en el borde superior del Sol. La Luna está en marcha.",
        "obscuration_20": "Veinte por ciento del disco solar está cubierto. Todavía parece una tarde normal de agosto aquí en León. Pero eso está a punto de cambiar.",
        "temperature_drop": "La temperatura empieza a bajar. El Sol pierde fuerza. Puede que sintáis los primeros escalofríos mientras la Luna bloquea cada vez más energía.",
        "sharp_shadows": "Mirad las sombras en el suelo. ¿Veis cómo los bordes se están afilando? Es porque el Sol se está convirtiendo en una media luna muy fina — una fuente lineal de luz en vez de un disco.",
        "sky_darkens": "El cielo está visiblemente más oscuro. Dos tercios del Sol han desaparecido. Mirad alrededor — los colores del paisaje se desvanecen, volviéndose grises y metálicos. La luz ya no es normal.",
        "weather_changes": "¿Lo sentís? El aire está cambiando. La temperatura ha bajado varios grados. Puede que notéis una brisa cambiando de dirección mientras la sombra lunar altera la atmósfera.",
        "light_colors": "Ochenta por ciento cubierto. La luz es de otro mundo — plana, gris, desaturada. Todo parece una fotografía desteñida. Vuestro cerebro sabe que algo está profundamente mal.",
        "venus_appears": "¡Mirad al suroeste! Venus se ha hecho visible a simple vista. Una joya brillante en el cielo que se oscurece. Todavía quedan diez minutos para la totalidad.",
        "nature_reacts": "Escuchad. Los pájaros se están callando. Algunos se dirigen a dormir, confundidos por el crepúsculo prematuro. Los insectos nocturnos despiertan. La naturaleza ha sido engañada.",
        "dark_shadow_approaching": "Girad hacia el oeste-noroeste. ¿Veis esa oscuridad en el horizonte? Esa es la sombra de la Luna — corriendo hacia nosotros a mil quinientos kilómetros por hora cruzando el Atlántico. Viene. Y tiene vuestro nombre.",
        "shadow_bands_pre": "¡Bandas de sombra! Mirad cualquier superficie blanca plana — ondas de luz, como el fondo de una piscina. La atmósfera está doblando los últimos rayos de sol.",
        "corona_appears": "¡Veinte segundos! La corona — la atmósfera exterior del Sol — se hace visible alrededor de la Luna. Un anillo blanco fantasmal. Es el momento.",
        "shadow_sweeps_in": "¡La sombra está AQUÍ! ¡Quince segundos! ¡La oscuridad llega del oeste como un maremoto sobre la llanura!",
        "diamond_ring_pre": "¡ANILLO DE DIAMANTE! ¡El último trozo de Sol brilla como una joya contra la corona! ¡Diez segundos para la totalidad!",
        "bailys_beads_pre": "¡Perlas de Baily! ¡Puntos de luz a través de los valles de la Luna! Filtros fuera en cinco — cuatro — tres — dos — uno —",
        "c2_totality": "¡TOTALIDAD! ¡FILTROS FUERA! ¡El Sol ha DESAPARECIDO! ¡El día se ha convertido en NOCHE sobre León! ¡Mirad! ¡MIRAD!",
        "chromosphere": "¡La cromosfera! Ese fino anillo rosa-rojo en el borde de la Luna — la atmósfera inferior del Sol, ¡normalmente invisible! ¡Y mirad — prominencias! ¡Lazos rojos de plasma! ¡El máximo solar cumple!",
        "corona_full": "La corona en toda su gloria. Chorros blancos extendiéndose millones de kilómetros en todas direcciones. Venus brilla al suroeste. Estáis dentro de un atardecer de trescientos sesenta grados.",
        "maximum_eclipse": "¡ECLIPSE MÁXIMO! Las veinte horas, veintinueve minutos y dieciocho segundos. La Luna perfectamente centrada en el Sol. Magnitud uno coma cero uno cero. Saboread esto — quedan cuarenta y seis segundos.",
        "totality_warning": "Treinta segundos de totalidad. Absorbed todo. La corona. El resplandor del horizonte. Las estrellas. Grabadlo en vuestra memoria. Lo llevaréis el resto de vuestras vidas.",
        "chromosphere_returns": "¡Cinco segundos! ¡La cromosfera brilla en el borde trasero! ¡Preparad los filtros — FILTROS PUESTOS!",
        "c3_totality_ends": "¡TERCER CONTACTO! ¡FILTROS PUESTOS — YA! ¡La totalidad ha TERMINADO! Un minuto y treinta y dos segundos de pura magia. ¡El anillo de diamante brilla en el otro lado!",
        "bailys_beads_post": "Perlas de Baily de nuevo en el borde trasero. El Sol lucha por abrirse paso a través de los valles lunares.",
        "diamond_ring_post": "El segundo Anillo de Diamante aparece resplandeciente. Una joya de luz solar contra la corona que se desvanece. Bienvenido de vuelta, Sol. Te echamos de menos.",
        "shadow_sweeps_out": "La sombra se aleja corriendo hacia el este. Mirad cómo se va — mil quinientos kilómetros por hora, rumbo al Mediterráneo.",
        "corona_fades": "La corona se desvanece. No la volveréis a ver hasta el próximo eclipse total. Atesorad ese recuerdo.",
        "shadow_horizon_retreat": "La sombra de la Luna se retira por el horizonte oriental. Todavía se ve — una mancha oscura contra el cielo vespertino, cada segundo más pequeña.",
        "nature_returns": "La naturaleza se recupera. Los pájaros cantan de nuevo. El mundo vuelve a la normalidad. Pero vosotros? Vosotros nunca volveréis a ser los mismos.",
        "light_returns": "La luz y la temperatura vuelven a la normalidad. Pero el Sol ya está bajo — todavía parcialmente eclipsado mientras se hunde hacia el oeste.",
        "eclipse_sunset": "Aquí viene — el Sol eclipsado encontrándose con el atardecer. Un Sol en media luna hundiéndose en un horizonte naranja. Esta imagen no volverá a ocurrir en León hasta el año dos mil ciento ochenta.",
        "sunset": "El Sol se pone — todavía con la sombra de la Luna en su cara. Un atardecer eclipsado. Extraordinario. El eclipse continúa bajo el horizonte, pero para nosotros, el espectáculo ha terminado.",
        "c4_fourth_contact": "Cuarto contacto. Veintiuna veintidós. La Luna se ha ido. Una hora, cuarenta y nueve minutos y treinta y dos segundos de teatro celestial. Qué privilegio. Gracias por estar aquí.",
    },
}

# Dramatic events — these get slower delivery rate
DRAMATIC_IDS = {
    "dark_shadow_approaching",
    "corona_appears",
    "shadow_sweeps_in",
    "diamond_ring_pre",
    "bailys_beads_pre",
    "c2_totality",
    "chromosphere",
    "corona_full",
    "maximum_eclipse",
    "totality_warning",
    "chromosphere_returns",
    "c3_totality_ends",
    "diamond_ring_post",
    "eclipse_sunset",
    "light_colors",
}

# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

async def generate_clip(clip_id: str, text: str, lang: str, voice: str, rate: str, output_path: Path):
    """Generate a single TTS clip."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output_path))
    
    size_kb = output_path.stat().st_size / 1024
    print(f"  ✓ {lang}/{clip_id}.mp3 ({size_kb:.0f} KB)")


async def generate_all():
    """Generate all clips for both languages."""
    total = 0
    errors = []
    
    for lang, scripts in SCRIPTS.items():
        voice = VOICES[lang]
        print(f"\n{'='*60}")
        print(f"Generating {lang.upper()} clips with voice: {voice}")
        print(f"{'='*60}")
        
        for clip_id, text in scripts.items():
            rate = RATE_DRAMATIC if clip_id in DRAMATIC_IDS else RATE_NORMAL
            output_path = OUTPUT_DIR / lang / f"{clip_id}.mp3"
            
            # Skip if already generated (for resumability)
            if output_path.exists() and output_path.stat().st_size > 100:
                size_kb = output_path.stat().st_size / 1024
                print(f"  · {lang}/{clip_id}.mp3 (exists, {size_kb:.0f} KB)")
                total += 1
                continue
            
            try:
                await generate_clip(clip_id, text, lang, voice, rate, output_path)
                total += 1
            except Exception as e:
                print(f"  ✗ {lang}/{clip_id}: {e}")
                errors.append(f"{lang}/{clip_id}")
    
    return total, errors


def encode_to_js():
    """Encode all generated MP3s to base64 and write audio-clips.js."""
    print(f"\n{'='*60}")
    print("Encoding to base64 JavaScript...")
    print(f"{'='*60}")
    
    clips = {"en": {}, "es": {}}
    total_size = 0
    
    for lang in ["en", "es"]:
        lang_dir = OUTPUT_DIR / lang
        if not lang_dir.exists():
            continue
        
        for mp3_file in sorted(lang_dir.glob("*.mp3")):
            clip_id = mp3_file.stem
            data = mp3_file.read_bytes()
            b64 = base64.b64encode(data).decode("ascii")
            clips[lang][clip_id] = f"data:audio/mpeg;base64,{b64}"
            total_size += len(data)
            print(f"  ✓ {lang}/{clip_id} ({len(data)/1024:.0f} KB → {len(b64)/1024:.0f} KB b64)")
    
    # Write JS file
    js_content = "// Auto-generated by generate-audio.py — DO NOT EDIT\n"
    js_content += f"// Total audio size: {total_size/1024:.0f} KB ({total_size/1024/1024:.1f} MB)\n"
    js_content += f"// Clips: {sum(len(v) for v in clips.values())} ({len(clips['en'])} EN + {len(clips['es'])} ES)\n\n"
    js_content += "const AUDIO_CLIPS = " + json.dumps(clips, indent=2) + ";\n"
    
    JS_OUTPUT.write_text(js_content, encoding="utf-8")
    print(f"\n✓ Written {JS_OUTPUT} ({JS_OUTPUT.stat().st_size / 1024:.0f} KB)")
    print(f"  Total audio: {total_size/1024:.0f} KB ({total_size/1024/1024:.1f} MB)")
    
    return total_size


async def main():
    print("Eclipse Commentator — Audio Generator")
    print("=" * 60)
    print(f"Voices: EN={VOICES['en']}, ES={VOICES['es']}")
    print(f"Clips: {len(SCRIPTS['en'])} EN + {len(SCRIPTS['es'])} ES = {len(SCRIPTS['en']) + len(SCRIPTS['es'])} total")
    print(f"Output: {OUTPUT_DIR}/ and {JS_OUTPUT}")
    
    # Step 1: Generate MP3 files
    total, errors = await generate_all()
    
    if errors:
        print(f"\n⚠ {len(errors)} clips failed: {', '.join(errors)}")
        print("Re-run the script to retry failed clips.")
    
    print(f"\n✓ Generated {total} clips")
    
    # Step 2: Encode to JavaScript
    total_size = encode_to_js()
    
    # Step 3: Print injection instructions
    print(f"\n{'='*60}")
    print("NEXT STEPS")
    print(f"{'='*60}")
    print(f"1. Review audio clips in audio/en/ and audio/es/")
    print(f"2. Run: python3 inject-audio.py")
    print(f"   This will embed the audio into eclipse.html")
    print(f"")
    print(f"Or manually: copy the AUDIO_CLIPS object from {JS_OUTPUT}")
    print(f"into eclipse.html, replacing the empty AUDIO_CLIPS object.")
    print(f"")
    if total_size > 5 * 1024 * 1024:
        print(f"⚠ Total audio is {total_size/1024/1024:.1f} MB — consider reducing")
        print(f"  quality or using ElevenLabs only for dramatic moments.")


if __name__ == "__main__":
    asyncio.run(main())
