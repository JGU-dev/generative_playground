import copy
from nltk.grammar import Nonterminal, Production, is_nonterminal
import nltk

pre_grammar_string_zinc_new = """
smiles -> nonH_bond
smiles -> initial_valence_1 bond
smiles -> initial_valence_2 double_bond
smiles -> initial_valence_3 triple_bond
initial_valence_1 -> 'F'
initial_valence_1 -> 'Cl'
initial_valence_1 -> 'Br'
initial_valence_1 -> 'I'
initial_valence_1 -> '[' 'O' '-' ']'
initial_valence_1 -> '[' 'N' 'H' '3' '+' ']'
initial_valence_2 -> 'O'
initial_valence_2 -> 'S'
initial_valence_3 -> '[' 'C' '@' 'H' ']'
initial_valence_3 -> '[' 'C' '@' '@' 'H' ']'
initial_valence_3 -> 'N'
initial_valence_3 -> '[' 'N' 'H' '+' ']'
bond -> 'h'
bond -> nonH_bond
branch -> 'h'
branch -> '(' nonH_bond ')'
nonH_bond -> valence_1
nonH_bond -> valence_2 bond
nonH_bond -> valence_3 double_bond
nonH_bond -> valence_4 triple_bond
double_bond -> '=' valence_2
double_bond -> '=' valence_3 bond
double_bond -> '=' valence_4 double_bond
triple_bond -> '#' valence_3 
triple_bond -> '#' valence_4 bond
valence_4 -> 'C'
valence_4 -> '[' 'C' '@' ']'
valence_4 -> '[' 'C' '@' '@' ']'
valence_4 -> '[' 'N' '+' ']'
valence_3 -> '[' 'C' '@' 'H' ']'
valence_3 -> '[' 'C' '@' '@' 'H' ']'
valence_3 -> 'N'
valence_3 -> '[' 'N' 'H' '+' ']'
valence_3 -> valence_4 branch
valence_2 -> 'O'
valence_2 -> 'S'
valence_2 -> 'S' '(' '=' 'O' ')'  '(' '=' 'O' ')'
valence_2 -> valence_3 branch
valence_2 -> valence_4 '(' double_bond ')'
valence_1 -> 'F'
valence_1 -> 'Cl'
valence_1 -> 'Br'
valence_1 -> 'I'
valence_1 -> '[' 'O' '-' ']'
valence_1 -> '[' 'N' 'H' '3' '+' ']'
valence_1 -> valence_2  branch
valence_1 -> valence_3 '(' double_bond ')'
valence_1 -> valence_4 '(' triple_bond ')'
nonH_bond -> valence_2 slash valence_3 '=' valence_3 slash valence_2
slash -> '/'
slash -> '\\'
nonH_bond -> aliphatic_ring
aliphatic_ring -> valence_3_num cycle_bond
aliphatic_ring -> valence_4_num cycle_double_bond
valence_2 -> vertex_attached_ring
vertex_attached_ring -> valence_4_num '(' cycle_bond ')'
cycle_bond -> valence_2 cycle_bond
cycle_bond -> valence_3 cycle_double_bond
cycle_double_bond -> '=' valence_3 cycle_bond
cycle_bond -> valence_2_num
cycle_double_bond -> '=' valence_3_num
nonH_bond -> aliphatic_ring_segment bond
cycle_bond -> aliphatic_ring_segment cycle_bond
aliphatic_ring_segment -> valence_3 '(' cycle_bond ')' valence_3_num
aliphatic_ring_segment -> valence_4 '(' cycle_bond ')' '=' valence_4_num
aliphatic_ring_segment -> valence_4 '(' cycle_double_bond ')' valence_3_num
nonH_bond -> aromatic_ring_5
nonH_bond -> aromatic_ring_6
starting_aromatic_c_num -> 'c' num
aromatic_atom -> 'n' 
aromatic_atom -> 'c' branch 
aromatic_os -> 'o'
aromatic_os -> 's'
aromatic_os -> 'n' '(' nonH_bond ')'
aromatic_os -> '[' 'n' 'H' ']'
aromatic_atom_num -> 'n' num
aromatic_atom_num -> 'c' num bond
aromatic_os_num -> 'o' num
aromatic_os_num -> 's' num
aromatic_os_num -> 'n' num nonH_bond
nonH_bond -> double_aromatic_ring
double_aromatic_ring -> 'c' num1 aromatic_atom aromatic_atom aromatic_atom 'c' num 'c' num1 aromatic_atom aromatic_atom aromatic_atom aromatic_atom_num
double_aromatic_ring -> 'c' num1 aromatic_atom aromatic_atom aromatic_atom 'c' num 'n' num1 aromatic_atom aromatic_atom aromatic_atom_num
double_aromatic_ring -> 'c' num1 aromatic_atom aromatic_atom aromatic_atom 'n' num 'c' num1 aromatic_atom aromatic_atom aromatic_atom_num
aromatic_ring_6 -> starting_aromatic_c_num aromatic_atom full_aromatic_segment aromatic_atom aromatic_atom_num
aromatic_ring_6 -> starting_aromatic_c_num full_aromatic_segment full_aromatic_segment aromatic_atom_num
aromatic_ring_5 -> starting_aromatic_c_num aromatic_os full_aromatic_segment  aromatic_atom_num
aromatic_ring_5 -> starting_aromatic_c_num aromatic_atom aromatic_os aromatic_atom aromatic_atom_num
aromatic_ring_5 -> starting_aromatic_c_num full_aromatic_segment aromatic_os aromatic_atom_num
aromatic_ring_5 -> starting_aromatic_c_num full_aromatic_segment aromatic_atom aromatic_os_num
aromatic_ring_5 -> starting_aromatic_c_num aromatic_atom full_aromatic_segment aromatic_os_num
full_aromatic_segment -> aromatic_atom aromatic_atom
aromatic_os -> side_aliphatic_ring
side_aliphatic_ring -> 'c' num '(' cycle_bond ')'
full_aromatic_segment -> side_aliphatic_ring_segment
side_aliphatic_ring_segment -> 'c' num 'c' '(' cycle_bond ')'
side_aliphatic_ring_segment -> 'c' '(' cycle_bond ')' 'c' num
"""

"""


starting_aromatic_c_num -> '-' 'c' num 
double_aromatic_ring -> 'c' num2 aa aa aa 'c' num 'n' num2 aa aa aa_num
"""

def add_numbered_valence(grammar_str:str):
    my_str = grammar_str.split('\n')
    my_str_new = copy.copy(my_str)
    num_token = 'num'
    num_valences = ['valence_2', 'valence_3', 'valence_4']
    insert_points = ["']'","'S'", "'O'", "'C'", "'N'"]
    for s in my_str:
        if str(s[:9]) in num_valences and 'ring' not in s: # TODO: add a cleaner filter
            for nv in num_valences:
                s = s.replace(nv, nv + '_' + num_token)

            s_lhs, s_rhs = s.split(' -> ')
            # now try inserting num_token after the first actual atom we find
            for ip in insert_points:
                s_rhs_new = s_rhs.replace(ip, ip + ' ' + num_token)
                if s_rhs != s_rhs_new:
                    break

            my_str_new.append(s_lhs + ' -> ' + s_rhs_new)

    new_str = ''.join([s + '\n' for s in my_str_new])
    # print(new_str)
    # print('******************')
    return new_str

pre_grammar_string_zinc_new = add_numbered_valence(pre_grammar_string_zinc_new)

# nonH_bond -> plain_aromatic_ring
# add rules for generating ring numerals
for i in range(1,10):
    pre_grammar_string_zinc_new += "num -> '" + str(i) + "'\n"
    pre_grammar_string_zinc_new += "num1 -> '" + str(i) + "'\n"

for i in range(10,20):#20):#
    pre_grammar_string_zinc_new += "num -> '%" + str(i) + "'\n"
    pre_grammar_string_zinc_new += "num1 -> '%" + str(i) + "'\n"

pre_grammar_string_zinc_new += "Nothing -> None\n"

def compact_nonterminal(x: str, nont: Nonterminal):
    GCFG = nltk.CFG.fromstring(x)
    prods = GCFG.productions()
    lhs_prods = [p for p in prods if p.lhs() == nont]
    old_prods = [p for p in prods if p not in lhs_prods]

    while True:
        new_prods = []
        for p in old_prods:
            if nont in p.rhs():
                # find first occurrence
                for i, t in enumerate(p.rhs()):
                    if t == nont:
                        break
                # now apply each replacement rule in turn
                for lhsp in lhs_prods:
                    if i < len(p.rhs()) - 1: # if it's not the last token
                        new_rhs = p.rhs()[:i] + lhsp.rhs() + p.rhs[(i+1):]
                    else:
                        new_rhs = p.rhs()[:i] + lhsp.rhs()
                    # purge implicit H while we're at it
                    #new_rhs = [x for x in new_rhs if x!="'h'"]
                    this_new_p = Production(p.lhs(), new_rhs)
                    new_prods.append(this_new_p)
            else:
                new_prods.append(p)

        if new_prods == old_prods:
            break
        old_prods = new_prods

    new_str = ''.join([str(p).replace('\\\\','\\') + '\n' for p in new_prods])
    # print(new_str)
    return new_str

def purge_implicit_h(x):
    GCFG = nltk.CFG.fromstring(x)
    old_prods = GCFG.productions()
    new_prods = []
    for p in old_prods:
        new_prods.append(Production(p.lhs(), [x for x in p.rhs() if x != 'h']))

    new_str = ''.join([str(p).replace('\\\\','\\') + '\n' for p in new_prods])
    # print(new_str)
    return new_str

pre_grammar_string_zinc_new = compact_nonterminal(pre_grammar_string_zinc_new, Nonterminal('bond'))
pre_grammar_string_zinc_new = compact_nonterminal(pre_grammar_string_zinc_new, Nonterminal('branch'))
pre_grammar_string_zinc_new = purge_implicit_h(pre_grammar_string_zinc_new)

propagate_strings = ['cycle', 'num']

def is_propagator(x):
    return is_nonterminal(x) and any([ps in x._symbol for ps in propagate_strings])

def test_cycle_propagation(x):
    GCFG = nltk.CFG.fromstring(x)
    for p in GCFG.productions():
        num_propagators = sum([1 if is_propagator(s) else 0 for s in p.rhs()])
        if 'ring' in p.lhs()._symbol:
            if 'double' in p.lhs()._symbol:
                assert(num_propagators == 4)
            else:
                assert(num_propagators == 2)
        elif is_propagator(p.lhs()) and p.lhs()._symbol not in ['num','num1']:
            assert(num_propagators == 1)
        else:
            assert(num_propagators == 0)

test_cycle_propagation(pre_grammar_string_zinc_new)
print('******************************')
grammar_string_zinc_new = pre_grammar_string_zinc_new#purge_implicit_H(pre_grammar_string_zinc_new)
print(grammar_string_zinc_new)
print('******************************')