"""Which BodyParts3D structures each identification card shows.

SPECS[deck] = {"target": "R"|"both", "ctx": "R"|"both", "muscles": bool, "cards": {card name: [regex, ...]}}
Regexes match whole structure names (lower case) among the skeletal and muscular systems. Cards that are not
whole structures (landmarks, joints, membranes, curves) are simply not listed and keep their textbook pictures.
"""


def B(name):            # a bone, either side
    return rf"(?:right |left )?{name}(?: bone)?"


def M(name):            # a muscle or one of its parts/heads/bellies, either side
    return rf"(?:[a-z ]+ (?:part|head|belly) of )?(?:right |left )?{name}(?: muscle)?"


ORD = "first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth"
CERV = rf"atlas|axis|(?:third|fourth|fifth|sixth|seventh) cervical vertebra"
THOR = r"(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth) thoracic vertebra"
LUMB = r"(?:first|second|third|fourth|fifth) lumbar vertebra"
RIBS = lambda ords: rf"(?:right |left )?(?:{ords}) rib"
CARPALS = r"(?:right |left )?(?:scaphoid|lunate|triquetral|pisiform|trapezium|trapezoid|capitate|hamate)"
FINGERS = r"(?:proximal|middle|distal) phalanx of (?:right |left )?(?:thumb|index finger|middle finger|ring finger|little finger)"
TOES = r"(?:proximal|middle|distal) phalanx of (?:right |left )?(?:big toe|second toe|third toe|fourth toe|little toe)"
TARSALS = r"(?:right |left )?(?:talus|calcaneus|cuboid bone|(?:medial|intermediate|lateral) cuneiform bone)|navicular bone of (?:right|left) foot"

SKULL_ALL = r"|".join([B(x) for x in ("frontal", "occipital", "sphenoid", "mandible", "vomer", "parietal", "temporal", "zygomatic",
                                       "maxilla", "nasal", "lacrimal", "palatine", "inferior nasal concha")] + ["ethmoid"])

SPECS = {
    "ch7-skull": {"target": "both", "ctx": "both", "muscles": False, "cards": {
        "Cranium": [B("frontal"), B("occipital"), B("sphenoid"), B("parietal"), B("temporal"), "ethmoid"],
        "Facial bones": [B("mandible"), B("vomer"), B("zygomatic"), B("maxilla"), B("nasal"), B("lacrimal"), B("palatine"), B("inferior nasal concha")],
        "Frontal bone": [B("frontal")], "Parietal bone": [B("parietal")], "Temporal bone": [B("temporal")],
        "Occipital bone": [B("occipital")], "Sphenoid bone": [B("sphenoid")], "Ethmoid bone": ["ethmoid"],
        "Maxilla": [B("maxilla")], "Mandible": [B("mandible")], "Zygomatic bone": [B("zygomatic")], "Nasal bone": [B("nasal")],
        "Lacrimal bone": [B("lacrimal")], "Palatine bone": [B("palatine")], "Vomer": [B("vomer")],
        "Inferior nasal concha": [B("inferior nasal concha")], "Hyoid bone": [B("hyoid")]}},
    "ch7-vert": {"target": "both", "ctx": "both", "muscles": False, "cards": {
        "Vertebral column": [CERV, THOR, LUMB, "sacrum"], "Cervical vertebrae": [CERV], "Thoracic vertebrae": [THOR],
        "Lumbar vertebrae": [LUMB], "Sacrum": ["sacrum"], "Atlas": ["atlas"], "Axis": ["axis"]}},
    "ch7-thor": {"target": "both", "ctx": "both", "muscles": False, "cards": {
        "Thoracic cage": [RIBS(ORD), "manubrium", "body of sternum", "xiphoid process", r"[a-z ]*costal cartilage", THOR],
        "Sternum": ["manubrium", "body of sternum", "xiphoid process"], "Manubrium": ["manubrium"],
        "Body of the sternum": ["body of sternum"], "Xiphoid process": ["xiphoid process"],
        "True ribs": [RIBS("first|second|third|fourth|fifth|sixth|seventh")],
        "False ribs": [RIBS("eighth|ninth|tenth")], "Floating ribs": [RIBS("eleventh|twelfth")],
        "Costal cartilage": [r"[a-z ]*costal cartilage"]}},
    "ch8-pect": {"target": "both", "ctx": "both", "muscles": False, "cards": {
        "Pectoral girdle": [B("clavicle"), B("scapula")], "Clavicle": [B("clavicle")], "Scapula": [B("scapula")]}},
    "ch8-arm": {"target": "R", "ctx": "R", "muscles": False, "cards": {
        "Humerus": [B("humerus")], "Ulna": [B("ulna")], "Radius": [B("radius")], "Scaphoid": [B("scaphoid")],
        "Pisiform": [B("pisiform")], "Hamate": [B("hamate")], "Carpal bones": [CARPALS],
        "Metacarpals": [r"(?:right |left )?(?:first|second|third|fourth|fifth) metacarpal bone"], "Phalanges": [FINGERS]}},
    "ch8-pelv": {"target": "both", "ctx": "both", "muscles": False, "cards": {
        "Hip bone": [B("hip bone")], "Pelvis": [B("hip bone"), "sacrum"], "Pelvic girdle": [B("hip bone")]}},
    "ch8-leg": {"target": "R", "ctx": "R", "muscles": False, "cards": {
        "Femur": [B("femur")], "Patella": [B("patella")], "Tibia": [B("tibia")], "Fibula": [B("fibula")],
        "Talus": [B("talus")], "Calcaneus": [B("calcaneus")], "Navicular": [r"navicular bone of (?:right|left) foot"],
        "Cuboid": [B("cuboid")], "Cuneiforms": [r"(?:right |left )?(?:medial|intermediate|lateral) cuneiform bone"],
        "Tarsal bones": [TARSALS], "Metatarsals": [r"(?:right |left )?(?:first|second|third|fourth|fifth) metatarsal bone"],
        "Phalanges": [TOES]}},
    "ch11-head": {"target": "R", "ctx": "both", "muscles": True, "cards": {
        "Orbicularis oris": [M("orbicularis oris")], "Orbicularis oculi": [M("orbicularis oculi")],
        "Occipitofrontalis": [M("frontalis"), M("occipitalis")], "Buccinator": [M("buccinator")],
        "Zygomaticus major": [M("zygomaticus major")], "Levator labii superioris": [M("levator labii superioris")],
        "Depressor anguli oris": [M("depressor anguli oris")], "Mentalis": [M("mentalis")], "Platysma": [M("platysma")],
        "Masseter": [M("masseter")], "Temporalis": [M("temporalis")], "Medial pterygoid": [M("medial pterygoid")],
        "Lateral pterygoid": [M("lateral pterygoid")], "Digastric": [M("digastric")], "Sternohyoid": [M("sternohyoid")]}},
    "ch11-resp": {"target": "R", "ctx": "both", "muscles": True, "cards": {
        "Diaphragm": [M("diaphragm")], "External intercostals": [M("external intercostal")],
        "Internal intercostals": [M("internal intercostal")], "Pectoralis minor": [M("pectoralis minor")],
        "Serratus anterior": [M("serratus anterior")], "Sternocleidomastoid": [M("sternocleidomastoid")],
        "Scalenes": [M("scalenus (?:anterior|medial|posterior)")], "Serratus posterior superior": [M("serratus posterior superior")],
        "Serratus posterior inferior": [M("serratus posterior inferior")], "Transversus thoracis": [M("transversus thoracis")]}},
    "ch11-back": {"target": "R", "ctx": "both", "muscles": True, "cards": {
        "Spinalis": [M(r"spinalis (?:thoracis|cervicis)")], "Longissimus": [M(r"longissimus (?:thoracis|capitis|cervicis)")],
        "Iliocostalis": [M(r"iliocostalis (?:lumborum|thoracis|cervicis)")],
        "Erector spinae": [M(r"spinalis (?:thoracis|cervicis)"), M(r"longissimus (?:thoracis|capitis|cervicis)"), M(r"iliocostalis (?:lumborum|thoracis|cervicis)")],
        "Quadratus lumborum": [M("quadratus lumborum")], "Splenius capitis": [M("splenius capitis")],
        "Splenius cervicis": [M("splenius cervicis")], "Semispinalis capitis": [M("semispinalis capitis")],
        "Semispinalis thoracis": [M("semispinalis thoracis")]}},
    "ch11-abd": {"target": "R", "ctx": "both", "muscles": True, "cards": {
        "Rectus abdominis": [M("rectus abdominis")], "External oblique": [M("external oblique")],
        "Internal oblique": [M("internal oblique")], "Transversus abdominis": [M("transversus abdominis")],
        "Linea alba": ["linea alba"]}},
    "ch11-sh": {"target": "R", "ctx": "both", "muscles": True, "cards": {
        "Deltoid": [M("deltoid")], "Pectoralis major": [M("pectoralis major")], "Latissimus dorsi": [M("latissimus dorsi")],
        "Supraspinatus": [M("supraspinatus")], "Infraspinatus": [M("infraspinatus")], "Teres minor": [M("teres minor")],
        "Subscapularis": [M("subscapularis")], "Teres major": [M("teres major")], "Coracobrachialis": [M("coracobrachialis")],
        "Rotator cuff": [M("supraspinatus"), M("infraspinatus"), M("teres minor"), M("subscapularis")],
        "Trapezius": [M("trapezius")], "Rhomboid major": [M("rhomboid major")], "Rhomboid minor": [M("rhomboid minor")],
        "Levator scapulae": [M("levator scapulae")]}},
    "ch11-arm": {"target": "R", "ctx": "R", "muscles": True, "cards": {
        "Biceps brachii": [M("biceps brachii")], "Brachialis": [M("brachialis")], "Brachioradialis": [M("brachioradialis")],
        "Triceps brachii": [M("triceps brachii")], "Anconeus": [M("anconeus")], "Pronator teres": [M("pronator teres")],
        "Pronator quadratus": [M("pronator quadratus")], "Supinator": [M("supinator")]}},
    "ch11-hand": {"target": "R", "ctx": "R", "muscles": True, "cards": {
        "Flexor carpi radialis": [M("flexor carpi radialis")], "Palmaris longus": [M("palmaris longus")],
        "Flexor carpi ulnaris": [M("flexor carpi ulnaris")], "Flexor digitorum superficialis": [M("flexor digitorum superficialis")],
        "Extensor carpi radialis longus": [M("extensor carpi radialis longus")], "Extensor carpi radialis brevis": [M("extensor carpi radialis brevis")],
        "Extensor digitorum": [M("extensor digitorum")], "Extensor digiti minimi": [M("extensor digiti minimi")],
        "Extensor carpi ulnaris": [M("extensor carpi ulnaris")], "Abductor pollicis longus": [M("abductor pollicis longus")],
        "Extensor pollicis longus": [M("extensor pollicis longus")], "Extensor pollicis brevis": [M("extensor pollicis brevis")]}},
    "ch11-hip": {"target": "R", "ctx": "R", "muscles": True, "cards": {
        "Psoas major": [M("psoas major")], "Iliacus": [M("iliacus")], "Iliopsoas": [M("psoas major"), M("iliacus")],
        "Gluteus maximus": [M("gluteus maximus")], "Gluteus medius": [M("gluteus medius")], "Gluteus minimus": [M("gluteus minimus")],
        "Tensor fasciae latae": [M("tensor fasciae latae")]}},
    "ch11-thigh": {"target": "R", "ctx": "R", "muscles": True, "cards": {
        "Sartorius": [M("sartorius")], "Rectus femoris": [M("rectus femoris")], "Vastus lateralis": [M("vastus lateralis")],
        "Vastus medialis": [M("vastus medialis")], "Vastus intermedius": [M("vastus intermedius")],
        "Quadriceps femoris": [M("rectus femoris"), M("vastus lateralis"), M("vastus medialis"), M("vastus intermedius")],
        "Pectineus": [M("pectineus")], "Adductor longus": [M("adductor longus")], "Adductor brevis": [M("adductor brevis")],
        "Adductor magnus": [M("adductor magnus")], "Gracilis": [M("gracilis")], "Biceps femoris": [M("biceps femoris")],
        "Semitendinosus": [M("semitendinosus")], "Semimembranosus": [M("semimembranosus")],
        "Hamstrings": [M("biceps femoris"), M("semitendinosus"), M("semimembranosus")]}},
    "ch11-leg": {"target": "R", "ctx": "R", "muscles": True, "cards": {
        "Tibialis anterior": [M("tibialis anterior")], "Extensor digitorum longus": [M("extensor digitorum longus")],
        "Extensor hallucis longus": [M("extensor hallucis longus")], "Fibularis tertius": [M("fibularis tertius")],
        "Gastrocnemius": [M("gastrocnemius")], "Soleus": [M("soleus")], "Calcaneal tendon": [M("calcaneal tendon")]}},
}
