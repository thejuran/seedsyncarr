import inspect

def overrides(interface_class):
    """
    Decorator to check that decorated method is a valid override
    Source: https://stackoverflow.com/a/8313042
    :param interface_class: The super class
    """
    assert(inspect.isclass(interface_class)), "Overrides parameter must be a class type"

    def overrider(method):
        assert(method.__name__ in dir(interface_class)), "Method does not override super class"
        return method
    return overrider


def sanitize_log_value(value: str) -> str:
    """Escape CR/LF and control characters from a string before logging.

    Prevents log injection (CWE-117) by replacing CR and LF with their literal
    escape tokens (\\r and \\n), and neutralizing other C0 control characters
    (0x00–0x1F, including ESC 0x1B used in ANSI-escape injection, and TAB 0x09)
    plus DEL (0x7F) by rendering them as \\xHH hex escapes. This matches the
    behavior of the inline `.replace("\\n","\\\\n").replace("\\r","\\\\r")`
    copies it replaces (Plans 04/05), while adding full C0 + DEL coverage per
    REQUIREMENTS.md SEC-01 and CONTEXT D-01.

    C1 control characters (0x80–0x9F) are intentionally left unescaped to avoid
    corrupting legitimate multi-byte UTF-8 filename bytes. The CWE-117 attack
    surface (CRLF log forging and ANSI/terminal-escape injection) is fully
    covered by the C0 + DEL set.

    Args:
        value: Potentially untrusted string to sanitize before log interpolation.

    Returns:
        Sanitized string with CR/LF rendered as literal \\r/\\n tokens and all
        other C0 control characters plus DEL rendered as \\xHH hex escapes.
        Printable ASCII and printable Unicode (codepoint >= 0x20, excluding DEL)
        are returned unchanged.
    """
    # Step 1: escape CR and LF as their literal token representations.
    # These render as \r and \n respectively (not \x0d/\x0a) for continuity
    # with the three inline copies being replaced in Plans 04/05.
    result = value.replace("\r", "\\r").replace("\n", "\\n")

    # Step 2: neutralize remaining C0 control characters (0x00–0x1F, which
    # after Step 1 no longer includes CR 0x0D or LF 0x0A) plus DEL (0x7F).
    # Any other character (printable ASCII, printable Unicode, C1 range) is
    # left untouched.
    sanitized = []
    for ch in result:
        cp = ord(ch)
        if cp < 0x20 or cp == 0x7F:
            sanitized.append("\\x{:02x}".format(cp))
        else:
            sanitized.append(ch)
    return "".join(sanitized)
