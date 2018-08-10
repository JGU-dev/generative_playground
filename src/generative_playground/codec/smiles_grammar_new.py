grammar_string_zinc_new="""smiles -> branched_C
branched_C -> 'C' branch branch bond
branched_C -> 'C' '(' double_bond ')' bond
branched_C -> 'C' triple_bond
double_bond -> '=' 'O'
double_bond -> '=' 'S'
double_bond -> '=' 'N' bond
double_bond -> '=' 'C' branch bond
double_bond -> '=' 'C' double_bond
triple_bond -> '#' 'N'
triple_bond -> '#' 'C' bond
bond -> 'h'
bond -> nonH_bond
branch -> 'h'
branch -> '(' nonH_bond ')'
nonH_bond -> branched_C
nonH_bond -> 'F'
nonH_bond -> 'Cl'
nonH_bond -> 'Br'
nonH_bond -> 'I'
nonH_bond -> 'O' bond
nonH_bond -> 'N' double_bond
nonH_bond -> 'N' branch bond
nonH_bond -> 'S' bond
nonH_bond -> 'S' '(' '=' 'O' ')'  '(' '=' 'O' ')' bond
nonH_bond -> plain_aromatic_ring
plain_aromatic_ring -> 'c' num1 'c' branch 'c' branch 'c' branch 'c' branch 'c' num1 bond
"""

# add rules for generating ring numerals
for i in range(1,10):
    grammar_string_zinc_new += "num1 -> '" + str(i) + "'\n"

for i in range(10,50):
    grammar_string_zinc_new += "num1 -> '%" + str(i) + "'\n"

grammar_string_zinc_new += "Nothing -> None\n"