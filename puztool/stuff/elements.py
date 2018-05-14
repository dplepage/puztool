from collections import namedtuple

from .stufflist import StuffList

Element = namedtuple("Element", ["name", "abbrev", "number"])

_elements =[
    ('hydrogen', 'h', 1),
    ('helium', 'he', 2),
    ('lithium', 'li', 3),
    ('beryllium', 'be', 4),
    ('boron', 'b', 5),
    ('carbon', 'c', 6),
    ('nitrogen', 'n', 7),
    ('oxygen', 'o', 8),
    ('fluorine', 'f', 9),
    ('neon', 'ne', 10),
    ('sodium', 'na', 11),
    ('magnesium', 'mg', 12),
    ('aluminum', 'al', 13),
    ('silicon', 'si', 14),
    ('phosphorus', 'p', 15),
    ('sulfur', 's', 16),
    ('chlorine', 'cl', 17),
    ('argon', 'ar', 18),
    ('potassium', 'k', 19),
    ('calcium', 'ca', 20),
    ('scandium', 'sc', 21),
    ('titanium', 'ti', 22),
    ('vanadium', 'v', 23),
    ('chromium', 'cr', 24),
    ('manganese', 'mn', 25),
    ('iron', 'fe', 26),
    ('cobalt', 'co', 27),
    ('nickel', 'ni', 28),
    ('copper', 'cu', 29),
    ('zinc', 'zn', 30),
    ('gallium', 'ga', 31),
    ('germanium', 'ge', 32),
    ('arsenic', 'as', 33),
    ('selenium', 'se', 34),
    ('bromine', 'br', 35),
    ('krypton', 'kr', 36),
    ('rubidium', 'rb', 37),
    ('strontium', 'sr', 38),
    ('yttrium', 'y', 39),
    ('zirconium', 'zr', 40),
    ('niobium', 'nb', 41),
    ('molybdenum', 'mo', 42),
    ('technetium', 'tc', 43),
    ('ruthenium', 'ru', 44),
    ('rhodium', 'rh', 45),
    ('palladium', 'pd', 46),
    ('silver', 'ag', 47),
    ('cadmium', 'cd', 48),
    ('indium', 'in', 49),
    ('tin', 'sn', 50),
    ('antimony', 'sb', 51),
    ('tellurium', 'te', 52),
    ('iodine', 'i', 53),
    ('xenon', 'xe', 54),
    ('cesium', 'cs', 55),
    ('barium', 'ba', 56),
    ('lanthanum', 'la', 57),
    ('cerium', 'ce', 58),
    ('praseodymium', 'pr', 59),
    ('neodymium', 'nd', 60),
    ('promethium', 'pm', 61),
    ('samarium', 'sm', 62),
    ('europium', 'eu', 63),
    ('gadolinium', 'gd', 64),
    ('terbium', 'tb', 65),
    ('dysprosium', 'dy', 66),
    ('holmium', 'ho', 67),
    ('erbium', 'er', 68),
    ('thulium', 'tm', 69),
    ('ytterbium', 'yb', 70),
    ('lutetium', 'lu', 71),
    ('hafnium', 'hf', 72),
    ('tantalum', 'ta', 73),
    ('tungsten', 'w', 74),
    ('rhenium', 're', 75),
    ('osmium', 'os', 76),
    ('iridium', 'ir', 77),
    ('platinum', 'pt', 78),
    ('gold', 'au', 79),
    ('mercury', 'hg', 80),
    ('thallium', 'tl', 81),
    ('lead', 'pb', 82),
    ('bismuth', 'bi', 83),
    ('polonium', 'po', 84),
    ('astatine', 'at', 85),
    ('radon', 'rn', 86),
    ('francium', 'fr', 87),
    ('radium', 'ra', 88),
    ('actinium', 'ac', 89),
    ('thorium', 'th', 90),
    ('protactinium', 'pa', 91),
    ('uranium', 'u', 92),
    ('neptunium', 'np', 93),
    ('plutonium', 'pu', 94),
    ('americium', 'am', 95),
    ('curium', 'cm', 96),
    ('berkelium', 'bk', 97),
    ('californium', 'cf', 98),
    ('einsteinium', 'es', 99),
    ('fermium', 'fm', 100),
    ('mendelevium', 'md', 101),
    ('nobelium', 'no', 102),
    ('lawrencium', 'lr', 103),
    ('rutherfordium', 'rf', 104),
    ('dubnium', 'db', 105),
    ('seaborgium', 'sg', 106),
    ('bohrium', 'bh', 107),
    ('hassium', 'hs', 108),
    ('meitnerium', 'mt', 109),
    ('darmstadtium', 'ds', 110),
    ('roentgenium', 'rg', 111),
    ('copernicium', 'cn', 112),
    ('nihonium', 'nh', 113),
    ('flerovium', 'fl', 114),
    ('moscovium', 'mc', 115),
    ('livermorium', 'lv', 116),
    ('tennessine', 'ts', 117),
    ('oganesson', 'og', 118)]

elements = StuffList(_elements, Element)

table = '''
 __________________________________________________________________________
|   1   2   3   4   5   6   7   8   9   10  11  12  13  14  15  16  17  18 |
|                                                                          |
|1  H                                                                   He |
|                                                                          |
|2  Li  Be                                          B   C   N   O   F   Ne |
|                                                                          |
|3  Na  Mg                                          Al  Si  P   S   Cl  Ar |
|                                                                          |
|4  K   Ca  Sc  Ti  V   Cr  Mn  Fe  Co  Ni  Cu  Zn  Ga  Ge  As  Se  Br  Kr |
|                                                                          |
|5  Rb  Sr  Y   Zr  Nb  Mo  Tc  Ru  Rh  Pd  Ag  Cd  In  Sn  Sb  Te  I   Xe |
|                                                                          |
|6  Cs  Ba  La  Hf  Ta  W   Re  Os  Ir  Pt  Au  Hg  Tl  Pb  Bi  Po  At  Rn |
|                                                                          |
|7  Fr  Ra  Ac  Rf  Db  Sg  Bh  Hs  Mt  Ds  Rg  Cn  Nh  Fl  Mc  Lv  Ts  Og |
|__________________________________________________________________________|
|                                                                          |
|               La  Ce  Pr  Nd  Pm  Sm  Eu  Gd  Tb  Dy  Ho  Er  Tm  Yb  Lu |
|                                                                          |
|               Ac  Th  Pa  U   Np  Pu  Am  Cm  Bk  Cf  Es  Fm  Md  No  Lr |
|__________________________________________________________________________|
'''
