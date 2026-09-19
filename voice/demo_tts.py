import time

import config
from voice.speaker import Speaker
from voice.tts import PiperTTS

tts = PiperTTS(
    config.PIPER_EXE,
    config.PIPER_MODEL,
    length_scale=config.PIPER_LENGTH_SCALE,
    sentence_silence=config.PIPER_SENTENCE_SILENCE,
)
speaker = Speaker(tts, on_state=lambda s: print("estado:", s))

speaker.say(
    "Olha só, eu preciso que você preste muita atenção neste teste de fala porque estamos avaliando a sua capacidade de processar diferentes pontuações de forma natural: você realmente consegue entender a diferença de ritmo entre uma vírgula, um ponto final e uma interrogação bem posicionada? Se eu falar rápido demais, sem respirar, você se perde na entonação ou consegue modular a voz perfeitamente; além disso, como você reage quando encontra três pontos seguidos... e logo em seguida toma um susto com uma frase exclamativa que surge do nada! Que incrível ver esse sistema funcionando, mas me diga uma coisa: o tom da sua voz muda de verdade quando você faz uma pergunta complexa sobre o futuro da inteligência artificial ou tudo continua parecendo linear, artificial e engessado? Quero ver se você consegue ler números como 1, 2, 3 e símbolos como @ ou % sem travar, mantendo a fluidez até o ponto final."
    )

time.sleep(3)
speaker.pause()      # simula o comando "parar"
time.sleep(2)
speaker.resume()     # simula o comando "continuar"
speaker.wait()