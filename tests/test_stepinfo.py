import pytest

from mechanical_docs import stepinfo

INVENTOR_INCH = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('x'),'2;1');
ENDSEC;
DATA;
#543=DIMENSIONAL_EXPONENTS(1.,0.,0.,0.,0.,0.,0.);
#545=(
CONVERSION_BASED_UNIT('inch',#548)
LENGTH_UNIT()
NAMED_UNIT(#543)
);
#546=(
LENGTH_UNIT()
NAMED_UNIT(*)
SI_UNIT(.MILLI.,.METRE.)
);
#547=(
LENGTH_UNIT()
NAMED_UNIT(*)
SI_UNIT(.CENTI.,.METRE.)
);
#548=LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(25.4),#546);
#549=(
NAMED_UNIT(*)
PLANE_ANGLE_UNIT()
SI_UNIT($,.RADIAN.)
);
#550=(
NAMED_UNIT(*)
SI_UNIT($,.STERADIAN.)
SOLID_ANGLE_UNIT()
);
#575=(
GEOMETRIC_REPRESENTATION_CONTEXT(3)
GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#574))
GLOBAL_UNIT_ASSIGNED_CONTEXT((#545,#549,#550))
REPRESENTATION_CONTEXT('','3D')
);
ENDSEC;
END-ISO-10303-21;
"""


def test_fixture_step_files_declare_mm(fixture_dir):
    assert stepinfo.length_unit(fixture_dir / "assets" / "base.step") == "mm"
    assert stepinfo.length_unit(fixture_dir / "assets" / "pin.step") == "mm"


def test_inventor_inch_file_with_extra_mm_entities(tmp_path):
    p = tmp_path / "inch.step"; p.write_text(INVENTOR_INCH)
    assert stepinfo.length_unit(p) == "in"


def test_centimetre_context(tmp_path):
    p = tmp_path / "cm.step"; p.write_text(INVENTOR_INCH.replace("((#545,#549,#550))", "((#547,#549,#550))"))
    assert stepinfo.length_unit(p) == "cm"


def test_missing_context_or_disagreement(tmp_path):
    p = tmp_path / "none.step"; p.write_text("ISO-10303-21;\nDATA;\n#1=CARTESIAN_POINT('',(0.,0.,0.));\nENDSEC;\n")
    with pytest.raises(stepinfo.StepInfoError, match="no GLOBAL_UNIT_ASSIGNED_CONTEXT"):
        stepinfo.length_unit(p)
    two = INVENTOR_INCH.replace("ENDSEC;\nEND-ISO", "#600=(\nGLOBAL_UNIT_ASSIGNED_CONTEXT((#546,#549,#550))\n);\nENDSEC;\nEND-ISO")
    p2 = tmp_path / "two.step"; p2.write_text(two)
    with pytest.raises(stepinfo.StepInfoError, match="disagree"):
        stepinfo.length_unit(p2)
