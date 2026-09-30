"""
Resonance - the narration script, the single source of truth for words.

Each line has:
  id     - used by the timeline, the subtitles and the audio files
  scene  - which scene it belongs to
  en     - the English text as it appears in the subtitles
  say    - what the voice engine reads (numbers spelled out so they are
           pronounced correctly); if missing, `en` is read as it is
  fr, ar - subtitle translations (Arabic: have a native speaker check it)
  gap    - seconds of silence after the line, before the next one starts

British spelling, no em dashes (house rules, see CLAUDE.md).
"""

LINES = [
    # 1 - Hook: two swings
    dict(id="L01", scene="hook",
         en="Two identical swings. Every push is exactly the same size.",
         fr="Deux balançoires identiques. Chaque poussée a exactement la même force.",
         ar="أرجوحتان متطابقتان. كل دفعة لها القوة نفسها تمامًا.",
         gap=0.6),
    dict(id="L02", scene="hook",
         en="On the left, one push per swing, always at the same moment. "
            "On the right, the same pushes, at random moments.",
         fr="À gauche, une poussée par aller-retour, toujours au même moment. "
            "À droite, les mêmes poussées, à des moments pris au hasard.",
         ar="على اليسار، دفعة واحدة في كل ذهاب وإياب، دائمًا في اللحظة نفسها. "
            "على اليمين، الدفعات نفسها، لكن في لحظات عشوائية.",
         gap=2.4),
    dict(id="L03", scene="hook",
         en="Same push. Different timing. A very different result.",
         fr="Même poussée. Moment différent. Un résultat très différent.",
         ar="الدفعة نفسها. توقيت مختلف. ونتيجة مختلفة جدًا.",
         gap=0.9),

    # 2 - Title
    dict(id="L04", scene="title",
         en="This is resonance.",
         fr="C'est la résonance.",
         ar="هذا هو الرنين.",
         gap=1.6),

    # 3 - Natural rhythm
    dict(id="L05", scene="rhythm",
         en="Anything that can wiggle has a natural rhythm: "
            "the beat it keeps when you pull it and let go.",
         fr="Tout ce qui peut osciller a un rythme naturel : "
            "celui qu'il garde quand on l'écarte puis qu'on le lâche.",
         ar="كل ما يمكنه أن يهتز له إيقاع طبيعي: "
            "الإيقاع الذي يحافظ عليه عندما تسحبه ثم تتركه.",
         gap=0.5),
    dict(id="L06", scene="rhythm",
         en="A swing on 2-metre chains goes back and forth about once every 2.8 seconds.",
         say="A swing on two metre chains goes back and forth about once every two point eight seconds.",
         fr="Une balançoire aux chaînes de 2 mètres fait un aller-retour environ toutes les 2,8 secondes.",
         ar="أرجوحة بسلاسل طولها 2 متر تذهب وتعود مرة كل 2.8 ثانية تقريبًا.",
         gap=1.2),
    dict(id="L07", scene="rhythm",
         en="Engineers study this with the simplest wiggler of all: a mass on a spring.",
         fr="Les ingénieurs l'étudient avec l'oscillateur le plus simple qui soit : une masse sur un ressort.",
         ar="يدرس المهندسون ذلك بأبسط جسم مهتز على الإطلاق: كتلة مربوطة بنابض.",
         gap=1.4),
    dict(id="L08", scene="rhythm",
         en="Its natural rhythm depends on just two things. "
            "A stiffer spring makes it faster. A heavier mass makes it slower.",
         fr="Son rythme naturel ne dépend que de deux choses. "
            "Un ressort plus raide le rend plus rapide. Une masse plus lourde le rend plus lent.",
         ar="إيقاعه الطبيعي يعتمد على شيئين فقط. "
            "النابض الأكثر صلابة يجعله أسرع. والكتلة الأثقل تجعله أبطأ.",
         gap=1.2),

    # 4 - The sweep
    dict(id="L09", scene="sweep",
         en="Now let's push it, gently, at a rhythm we choose.",
         fr="Maintenant, poussons-la doucement, au rythme que nous choisissons.",
         ar="لندفعها الآن بلطف، بالإيقاع الذي نختاره.",
         gap=0.8),
    dict(id="L10", scene="sweep",
         en="Push slowly, and the mass simply follows the push.",
         fr="Si l'on pousse lentement, la masse suit simplement la poussée.",
         ar="إذا دفعنا ببطء، تتبع الكتلة الدفعة ببساطة.",
         gap=1.0),
    dict(id="L11", scene="sweep",
         en="Push faster, closer to its natural rhythm, and the motion starts to grow.",
         fr="Poussons plus vite, plus près de son rythme naturel : le mouvement commence à grandir.",
         ar="وإذا دفعنا أسرع، أقرب إلى إيقاعها الطبيعي، تبدأ الحركة في الازدياد.",
         gap=0.8),
    dict(id="L12", scene="sweep",
         en="Right at its natural rhythm, the motion is ten times bigger than a slow push can make it.",
         fr="Pile à son rythme naturel, le mouvement est dix fois plus grand qu'avec une poussée lente.",
         ar="عند إيقاعها الطبيعي تمامًا، تصبح الحركة أكبر بعشر مرات مما تحدثه دفعة بطيئة.",
         gap=0.9),
    dict(id="L13", scene="sweep",
         en="Here is the secret: at resonance, every push goes the same way the mass is already moving. "
            "So every push adds energy.",
         fr="Voici le secret : à la résonance, chaque poussée va dans le sens où la masse bouge déjà. "
            "Chaque poussée ajoute donc de l'énergie.",
         ar="وهذا هو السر: عند الرنين، كل دفعة تكون في الاتجاه الذي تتحرك فيه الكتلة أصلًا. "
            "لذلك تضيف كل دفعة طاقة.",
         gap=1.0),
    dict(id="L14", scene="sweep",
         en="Push faster still, and the mass cannot keep up. It barely moves.",
         fr="Encore plus vite, et la masse n'arrive plus à suivre. Elle bouge à peine.",
         ar="وإذا دفعنا أسرع من ذلك، لا تستطيع الكتلة المواكبة. بالكاد تتحرك.",
         gap=1.2),

    # 5 - Damping
    dict(id="L15", scene="damping",
         en="So what stops the motion growing forever? Damping: anything that turns motion into heat, "
            "like friction, or the oil in a shock absorber.",
         fr="Qu'est-ce qui empêche le mouvement de grandir sans fin ? L'amortissement : tout ce qui "
            "transforme le mouvement en chaleur, comme le frottement, ou l'huile d'un amortisseur.",
         ar="فما الذي يمنع الحركة من الازدياد إلى ما لا نهاية؟ التخميد: كل ما يحوّل الحركة إلى حرارة، "
            "مثل الاحتكاك، أو الزيت داخل ممتص الصدمات.",
         gap=0.6),
    dict(id="L16", scene="damping",
         en="Damping sets the height of the peak. With 5 % damping, the motion is ten times bigger. "
            "Double the damping, and the peak halves. At 30 %, only a gentle bump is left.",
         say="Damping sets the height of the peak. With five percent damping, the motion is ten times bigger. "
             "Double the damping, and the peak halves. At thirty percent, only a gentle bump is left.",
         fr="L'amortissement fixe la hauteur du pic. Avec 5 % d'amortissement, le mouvement est dix fois "
            "plus grand. Doublez l'amortissement, et le pic est divisé par deux. À 30 %, il ne reste qu'une "
            "petite bosse.",
         ar="التخميد يحدد ارتفاع القمة. مع تخميد 5 %، تكون الحركة أكبر بعشر مرات. "
            "ضاعف التخميد، فتنخفض القمة إلى النصف. وعند 30 %، لا تبقى إلا حدبة صغيرة.",
         gap=0.8),
    dict(id="L17", scene="damping",
         en="That is why engineers add damping to anything that must not shake.",
         fr="C'est pourquoi les ingénieurs ajoutent de l'amortissement à tout ce qui ne doit pas trembler.",
         ar="لهذا يضيف المهندسون التخميد إلى كل ما يجب ألّا يهتز.",
         gap=1.4),

    # 6 - Millennium Bridge
    dict(id="L18", scene="bridge",
         en="London, June 2000. The Millennium Bridge opens, and thousands of people walk across.",
         say="London, June two thousand. The Millennium Bridge opens, and thousands of people walk across.",
         fr="Londres, juin 2000. Le Millennium Bridge ouvre au public, et des milliers de personnes le traversent.",
         ar="لندن، يونيو 2000. يُفتتح جسر الألفية، ويعبره آلاف الناس.",
         gap=0.6),
    dict(id="L19", scene="bridge",
         en="Every step pushes the deck a tiny bit sideways: left, right, left, right.",
         fr="Chaque pas pousse le tablier un tout petit peu sur le côté : gauche, droite, gauche, droite.",
         ar="كل خطوة تدفع سطح الجسر قليلًا جدًا إلى الجانب: يسارًا، يمينًا، يسارًا، يمينًا.",
         gap=0.6),
    dict(id="L20", scene="bridge",
         en="Once the deck starts to sway, people shift their feet to keep their balance. "
            "On average, those pushes go the same way the deck is already moving, "
            "so every step feeds the sway.",
         fr="Dès que le tablier commence à osciller, les gens déplacent leurs pieds pour garder "
            "l'équilibre. En moyenne, ces poussées vont dans le sens où le tablier bouge déjà : "
            "chaque pas nourrit l'oscillation.",
         ar="وما إن يبدأ السطح في التمايل حتى يحرّك الناس أقدامهم ليحافظوا على توازنهم. "
            "وفي المتوسط، تكون تلك الدفعات في الاتجاه الذي يتحرك فيه السطح أصلًا، "
            "فتغذّي كل خطوة التمايل.",
         gap=0.8),
    dict(id="L21", scene="bridge",
         en="Two days later, the bridge is closed. Engineers fitted dampers that turn the sway into heat. "
            "In 2002, it reopened, steady.",
         say="Two days later, the bridge is closed. Engineers fitted dampers that turn the sway into heat. "
             "In two thousand and two, it reopened, steady.",
         fr="Deux jours plus tard, le pont est fermé. Les ingénieurs ont installé des amortisseurs qui "
            "transforment l'oscillation en chaleur. En 2002, il a rouvert, stable.",
         ar="بعد يومين، أُغلق الجسر. ركّب المهندسون مخمِّدات تحوّل التمايل إلى حرارة. "
            "وفي 2002، أُعيد افتتاحه، ثابتًا.",
         gap=1.4),

    # 7 - Taipei 101
    dict(id="L22", scene="taipei",
         en="Taipei 101 goes one step further. Near the top of the 508-metre tower hangs "
            "a 660-tonne steel ball, tuned to the tower's own rhythm.",
         say="Taipei one oh one goes one step further. Near the top of the five hundred and eight metre tower "
             "hangs a six hundred and sixty tonne steel ball, tuned to the tower's own rhythm.",
         fr="Taipei 101 va encore plus loin. Près du sommet de la tour de 508 mètres est suspendue "
            "une boule d'acier de 660 tonnes, accordée sur le rythme propre de la tour.",
         ar="برج تايبيه 101 يذهب أبعد من ذلك. قرب قمة البرج البالغ ارتفاعه 508 أمتار، "
            "تتدلى كرة فولاذية وزنها 660 طنًا، مضبوطة على إيقاع البرج نفسه.",
         gap=0.7),
    dict(id="L23", scene="taipei",
         en="When the wind makes the tower sway, the ball swings a quarter of a beat behind it, "
            "so its pull works against the motion.",
         fr="Quand le vent fait osciller la tour, la boule se balance avec un quart de temps de retard, "
            "si bien que sa traction s'oppose au mouvement.",
         ar="عندما تجعل الرياح البرج يتمايل، تتأرجح الكرة متأخرة عنه بربع إيقاع، "
            "فيعمل شدّها ضد الحركة.",
         gap=0.8),
    dict(id="L24", scene="taipei",
         en="Resonance, used to fight resonance.",
         fr="La résonance, utilisée pour combattre la résonance.",
         ar="الرنين، يُستخدم لمحاربة الرنين.",
         gap=1.6),

    # 8 - Takeaway
    dict(id="L25", scene="takeaway",
         en="Push something at its favourite rhythm, and tiny pushes make huge movements.",
         fr="Poussez quelque chose à son rythme préféré, et de toutes petites poussées font d'énormes mouvements.",
         ar="ادفع أي شيء بإيقاعه المفضّل، فتصنع الدفعات الصغيرة حركات هائلة.",
         gap=0.0),
]


def line(line_id):
    for item in LINES:
        if item["id"] == line_id:
            return item
    raise KeyError(line_id)
