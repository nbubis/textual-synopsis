from lib.genalog_lcs import LCS


def test_lcs():
    s1 = "ABCD"
    s2 = "ACD"
    lcs = LCS(s1, s2)
    print(f"LCS('{s1}', '{s2}') = '{lcs.get_str()}' (Len: {lcs.get_len()})")
    assert lcs.get_str() == "ACD"

    s1 = "ABCDEF"
    s2 = "ABXDF"  # Common: AB DF = ABDF (X skipped, C, E skipped)
    lcs = LCS(s1, s2)
    print(f"LCS('{s1}', '{s2}') = '{lcs.get_str()}' (Len: {lcs.get_len()})")
    assert lcs.get_str() == "ABDF"

    s1 = "The planet Mars"
    s2 = "The plamet Maris"
    lcs = LCS(s1, s2)
    print(f"LCS('{s1}', '{s2}') = '{lcs.get_str()}'")

    print("Test passed!")


if __name__ == "__main__":
    test_lcs()
