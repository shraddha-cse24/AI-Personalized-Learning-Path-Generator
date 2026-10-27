"""
Builds data/topic_titles.csv and data/area_names.json from Info_Content.csv + Member 2's lookup.
 * title_zh : the most common exercise name inside the topic, with the 【基礎】/【一般】/【進階】 tag and the
             trailing exercise number removed (taken from the dataset itself, nothing invented).
 * title_en : English translation written by Claude. Machine translation -> have a Chinese speaker spot-check it.
 * area names: short English labels written by Claude from the topics each area contains.
"""
import json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
ic = pd.read_csv(ROOT / "data/Info_Content.csv", dtype=str)
lk = pd.read_csv(ROOT / "models/member2_exercise_lookup.csv", dtype={"ucid": str})

def clean(s):
    s = re.sub(r"^【[^】]+】", "", s).strip()
    s = re.sub(r"\s+[0-9０-９]+$", "", s).strip()
    return s

m = lk.merge(ic[["ucid", "content_pretty_name"]], on="ucid")
m["clean"] = m.content_pretty_name.map(clean)

EN = {
0:"Meaning and notation of powers",1:"Using symbols to represent numbers",2:"One-to-one correspondence counting",
3:"Quadrants a line passes through",4:"Combined add/subtract expressions and estimation (mixed exercises)",
5:"Ascending and descending order of polynomial terms",6:"Absolute value",7:"Equal ratios",
8:"Days, hours, minutes, seconds (mixed exercises)",9:"Kilograms and grams (mixed exercises)",
10:"Multiplying decimals by integers (mixed exercises)",11:"Liters and milliliters (mixed exercises)",
12:"Tables in daily life (mixed exercises)",13:"Equivalent fractions (mixed exercises)",
14:"Relationship between multiplication and division",15:"Reading clocks (whole hours)",
16:"Rates and applications (mixed exercises)",17:"Number order within 100",18:"Direct proportion calculations",
19:"Large units in daily life (mixed exercises)",20:"Square centimeters (mixed exercises)",
21:"Approximate numbers (mixed exercises)",22:"Hinge theorem",23:"Multiplying decimals (mixed exercises)",
24:"Dividing integers and decimals by integers (mixed exercises)",25:"Kilometers (mixed exercises)",
26:"Surface area of cubes and cuboids",27:"Numbers within 100 million (mixed exercises)",
28:"Prisms/cylinders, pyramids/cones and spheres",29:"Speed",
30:"Expanding, simplifying and common denominators (mixed exercises)",31:"Functional relationship formulas",
32:"Understanding pie charts",33:"Perimeter and area (mixed exercises)",34:"Factors and common factors (mixed exercises)",
35:"Adding/subtracting fractions with like denominators (mixed exercises)",36:"Sum of two quantities",
37:"Integer number line (mixed exercises)",38:"GCD and LCM (mixed exercises)",
39:"Numbers above 100 million (mixed exercises)",40:"Using proportional segments to identify parallel lines",
41:"Operations with continued ratios",42:"Angles, squares and rectangles (mixed exercises)",
43:"How to solve problems: quantitative relationships",44:"Dividing fractions (mixed exercises)",
45:"Two-decimal-place numbers (mixed exercises)",46:"Multi-digit multiplication and division (mixed exercises)",
47:"One-decimal-place numbers (mixed exercises)",48:"Vertical multiplication (mixed exercises)",
49:"Sectors (mixed exercises)",50:"Millimeters (mixed exercises)",51:"Line-symmetric figures",
52:"Numbers within 10,000 (mixed exercises)",53:"Two-step problems: subtraction and multiplication",
54:"Adding/subtracting fractions and integer multiples (mixed exercises)",55:"Common multiples and LCM",
56:"Multiples and common multiples (mixed exercises)",57:"Graphing solutions of linear inequalities",
58:"Volume: cubic centimeters (mixed exercises)",59:"Multiplying fractions (mixed exercises)",
60:"Multiplication and division with time",61:"Meaning of congruent triangles",62:"Reading and writing decimals",
63:"Quadrilaterals (mixed exercises)",64:"Two-digit quotients with a remainder",
65:"Capacity, volume and cubic measures (mixed exercises)",66:"Parallel and perpendicular relations between planes",
67:"Understanding circles (mixed exercises)",68:"Parallel lines and geometric figures",
69:"Calculations with two units (mixed exercises)",70:"Estimation (mixed exercises)",
71:"Triangles and polygons (mixed exercises)",72:"Interior and exterior angle sums of an n-gon",
73:"Dividing integers and fractions by integers (mixed exercises)",74:"Which date and which weekday",
75:"Adding and subtracting time (mixed exercises)",76:"Four operations with integers (mixed exercises)",
77:"Understanding division (mixed exercises)",78:"Two-step problems: successive division",79:"Understanding angles",
80:"Four operations with fractions and decimals (mixed exercises)",81:"Linear functions",
82:"Solving linear inequalities in one variable",83:"Boundary and perimeter (mixed exercises)",
84:"Expressing integer division results as fractions (mixed exercises)",85:"Function values from graphs",
86:"Mixed numbers and improper fractions (mixed exercises)",87:"Understanding fractions (mixed exercises)",
88:"Angle measures (mixed exercises)",89:"Adding/subtracting fractions with unlike denominators",
90:"Linear inequalities in one variable",91:"If ab = 0 then a = 0 or b = 0",
92:"Adding/subtracting multi-digit decimals (mixed exercises)",93:"Plotting points from coordinates",
94:"Scale drawings and map scales",95:"Triangles (mixed exercises)",96:"Multiplying integers",
97:"Two-step calculation rules (mixed exercises)",98:"Addition and subtraction within 10,000 (mixed exercises)",
99:"Counting days",100:"Multiplying integers (mixed exercises)",101:"Multiplying fractions",102:"Special quadrilaterals",
103:"Square roots (radicals)",104:"Adding numbers with different signs",
105:"Writing linear expressions in two variables",106:"Finding common factors",107:"Pi",
108:"Simple parallelogram problems",109:"Multiplication: multiples and tens/hundreds (mixed exercises)",
110:"Exponents and scientific notation",111:"Volume of prisms/cylinders (mixed exercises)",
112:"Solutions of linear equations in one variable",113:"Dividing decimals (mixed exercises)",
114:"Value of algebraic expressions",115:"Adding/subtracting fractions with unlike denominators (mixed exercises)",
116:"Areas of triangles and quadrilaterals (mixed exercises)",117:"Distributive law: monomial times binomial",
118:"Circles",119:"Volume of composite solids",120:"Direct proportion relationships",
121:"Two-step word problems: add/subtract and divide (mixed exercises)",122:"Factors and multiples",
123:"Two-step combined expressions: successive addition/subtraction (mixed exercises)",
124:"Distance between points and lines, and between lines",125:"Elimination by addition and subtraction",
126:"Polynomial multiplication",127:"Scaling plane figures",128:"Simplifying problems",
129:"Understanding bar charts and pie charts",
130:"Two-step combined expressions: multiplication or division with add/subtract (mixed exercises)",
131:"Ratios and ratio values (mixed exercises)",132:"Applications of arithmetic series",133:"Factors and multiples (junior)",
134:"Quantity problems",135:"Linear equations in one variable",136:"Systems of two linear equations",
137:"Adding/subtracting radicals: combining like radicals",138:"Completing the square",
139:"Reading bar charts and line charts: basics",140:"Ratios and proportions",
141:"Circumcenter and incenter of polygons",142:"Discount problems",
143:"Factoring with the difference-of-squares formula",144:"Probability of equally likely outcomes",
145:"Two-step combined expressions: successive multiplication/division (mixed exercises)",
146:"Extrema of y = ax^2 + bx + c",147:"Applications of angles outside a circle",
148:"Equality axioms for multiplication and division: integers",149:"Dividing integers (mixed exercises)",
150:"Perpendiculars and bisectors",151:"Exponents: paper folding and powers",
152:"Cross-multiplication factoring: positive constant term",153:"Compass-and-straightedge construction: angles",
154:"Vertices, edges and faces of prisms",155:"Similar figures",156:"Lines connecting midpoints of sides",
157:"Number sequence patterns",158:"Properties of tangents to a circle",
159:"Using the Pythagorean theorem to find right-triangle sides",160:"Coordinate plane",161:"Area of a circle",
162:"Algebraic proofs",163:"Graphs of single-term quadratic functions",164:"Understanding three-dimensional objects",
165:"Quadratic word problems: quantity type",166:"Mean (average)",167:"Understanding box plots",
168:"Geometric proofs and the three centers",169:"Quadratic functions: numerical problems",170:"Properties of cones",
}
assert len(EN) == 171

rows = []
for code, g in m.groupby("concept_code"):
    g = g.sort_values(["exercise_enc", "ucid"], ascending=[False, True])
    zh = g.clean.mode().iloc[0] if g.clean.duplicated().any() else g.clean.iloc[0]
    retiring = "即將下架" in zh
    zh = re.sub(r"\s*-\s*即將下架", "", zh).strip()
    rows.append({"concept_code": int(code), "concept_label": g.concept_label.iloc[0],
                 "title_zh": zh, "title_en": EN[int(code)], "retiring_on_junyi": retiring})
pd.DataFrame(rows).sort_values("concept_code").to_csv(ROOT / "data/topic_titles.csv", index=False, encoding="utf-8-sig")

AREAS = {"7f73q3": "Numbers and operations (elementary)", "ICgke8": "Problem solving (elementary)",
         "1EzKLz": "Geometry and measurement (elementary)", "jXSXg7": "Tables and graphs (elementary)",
         "xYDz4O": "Numbers, ratios and radicals (junior)", "R81Sqc": "Algebra and functions (junior)",
         "MfUX4B": "Geometry (junior)", "2YwsqJ": "Statistics and probability (junior)",
         "5Np4fx": "Exponents (senior)", "rzRcsB": "Distances (senior)"}
full = {}
for l2 in ic.level2_id.unique():
    key = next(k for k in AREAS if l2.startswith(k) or k in l2)
    full[l2] = AREAS[key]
assert len(full) == 10
json.dump(full, open(ROOT / "data/area_names.json", "w"), indent=1)
print("titles:", len(rows), "| retiring:", sum(r["retiring_on_junyi"] for r in rows), "| areas:", len(full))
