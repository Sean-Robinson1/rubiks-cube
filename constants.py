
SOLVED_MASK = 'WWWWWWWWWGGGGGGGGGRRRRRRRRRBBBBBBBBBOOOOOOOOOYYYYYYYYY'
FACE_NUM_TO_COLOUR = {0:'W',1:'G',2:'R',3:'B',4:'O',5:'Y'}
COLOUR_TO_FACE_NUM = {'W':0,'G':1,'R':2,'B':3,'O':4,'Y':5}
OPPOSITE_FACES = {0:5,1:3,2:4,3:1,4:2,5:0}
COLOURS = ['W', 'G', 'R', 'B', 'O', 'Y']
PLOTTING_COLOUR_MAP = {'W':'White','Y':'Yellow','B':'Blue','G':'Green','R':'Red','O':'Orange'}
COLOUR_TO_UNICODE = {'W':'⬜','G':'🟩','R':'🟥','B':'🟦','O':'🟧','Y':'🟨'}
ERROR_CHAR = '❔'
CLOCKWISE_TURNS = [2,5,8,7,6,3,0,1]
ANTI_CLOCKWISE_TURNS = [6,3,0,1,2,5,8,7]
SPIRAL_ORDER = [0,1,2,5,8,7,6,3]
OPPOSITE_FACE_MAPPING = {'R': 'O', 'B': 'G', 'W': 'Y', 'Y': 'W', 'G': 'B', 'O': 'R'}
# note this assumes white is on the top
LEFT_FACE_MAPPING = {'R': 'G', 'G': 'O', 'O': 'B', 'B': 'R'}
RIGHT_FACE_MAPPING = {'R': 'B', 'B': 'O', 'O': 'G', 'G': 'R'}
RELATIVE_FACE_MAPPING = {'B':{'F':'R','R':'B','B':'L','L':'F'},'G':{'F':'L','R':'F','B':'R','L':'B'},'O':{'F':'B','R':'L','B':'F','L':'R'}}

## WHITE CROSS

# solved masks for each white center piece for each face
WHITE_CROSS_SOLVED_MASKS = {
                ('G','...WW.....G..G........................................'),
                ('R','....W..W...........R..R...............................'),
                ('B','....WW......................B..B......................'),
                ('O','.W..W................................O..O.............')}

# masks that can be solved with a single FU'RU or F'U'RU move
WHITE_CROSS_INSERTION_MASKS = {
                    ('G', '...GW.....W..G........................................', "FU'RU"),
                    ('G', '....W........G..W...............................G.....', "F'U'RU"),
                    ('R', '....W..R...........W..R...............................', "FU'RU"),
                    ('R', '....W.................R..W....................R.......', "F'U'RU"),
                    ('B', '....WB......................W..B......................', "FU'RU"),
                    ('B', '....W..........................B..W...............B...', "F'U'RU"),
                    ('O', '.O..W................................W..O.............', "FU'RU"),
                    ('O', '....W...................................O..W........O.', "F'U'RU")
}

# a combination of all the above masks, used for recursion
WHITE_CROSS_RECURSION_MASKS = {
                '...WW.....G..G........................................',
                '....W..W...........R..R...............................',
                '....WW......................B..B......................',
                '.W..W................................O..O.............',
                '...GW.....W..G........................................',
                '....W..R...........W..R...............................',
                '....WB......................W..B......................',
                '.O..W................................W..O.............',
                '....W..........................B..W...............B...',
                '....W........G..W...............................G.....',
                '....W.................R..W....................R.......',
                '....W...................................O..W........O.'
                }

## F2L Corners

# the masks for the correctly placed corner pieces
F2L_CORNERS_SOLVED_MASKS =  {
                ('R','.W.WWW.WW.G..G.....RR.R....BB..B.....O..O.............'),
                ('B','.WWWWW.W..G..G.....R..R.....BB.B....OO..O.............'),
                ('O','WW.WWW.W.GG..G.....R..R.....B..B.....OO.O.............'),
                ('G','.W.WWWWW..GG.G....RR..R.....B..B.....O..O.............')}

# the masks for inserting each corner piece, with 3 different insertion methods per piece
F2L_CORNERS_INSERTION_MASKS = {
                    ('RB1','.W.WWW.W..G..G.....R..R...B.B..B.R...O..O......W......'),
                    ('RB2','.W.WWW.W..G..G.....R..R...R.B..B.W...O..O......B......'),
                    ('RB3','.W.WWW.W..G..G.....R..R...W.B..B.B...O..O......R......'),
                    ('BO1','.W.WWW.W..G..G.....R..R.....B..B...O.O..O.B..........W'),
                    ('BO2','.W.WWW.W..G..G.....R..R.....B..B...B.O..O.W..........O'),
                    ('BO3','.W.WWW.W..G..G.....R..R.....B..B...W.O..O.O..........B'),
                    ('OG1','.W.WWW.W..G..G.O...R..R.....B..B.....O..O...G......W..'),
                    ('OG2','.W.WWW.W..G..G.W...R..R.....B..B.....O..O...O......G..'),
                    ('OG3','.W.WWW.W..G..G.G...R..R.....B..B.....O..O...W......O..'),
                    ('GR1','.W.WWW.W..G..G...R.R..R.G...B..B.....O..O....W........'),
                    ('GR2','.W.WWW.W..G..G...G.R..R.W...B..B.....O..O....R........'),
                    ('GR3','.W.WWW.W..G..G...W.R..R.R...B..B.....O..O....G........')}

CORNER_INSERTION_ALGORITHMS = {1:"FLDDL'F'", 2:"R'D'R", 3:"FDF'"}