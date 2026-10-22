from mechanical_docs.names import slug, valid_identifier


def test_clean_ids_are_unchanged():
    assert slug("pin-a") == "pin-a" and slug("base") == "base" and slug("step-02") == "step-02"


def test_production_ids_become_unique_safe_slugs():
    a = slug("DATA\\COMMON\\McMaster\\MCMASTER 5537T293_T-Slotted Framing.ipt|[Primary]")
    b = slug("DATA\\COMMON\\McMaster\\MCMASTER 5537T429_T-Slotted Framing.ipt|[Primary]")
    assert a != b and a.startswith("data-common-mcmaster-mcmaster-5537t293") and "/" not in a and "\\" not in a and " " not in a
    assert len(a) <= 48 + 9
    assert slug("CAMERA FRAME:1/MCMASTER 5537T293_T-Slotted Framing:1") != slug("CAMERA FRAME:2/MCMASTER 5537T293_T-Slotted Framing:1")


def test_valid_identifier():
    assert valid_identifier("CAMERA FRAME:1/x:1") and valid_identifier("a|[Primary]")
    assert not valid_identifier("") and not valid_identifier(" pad ") and not valid_identifier("a\nb") and not valid_identifier(5)
