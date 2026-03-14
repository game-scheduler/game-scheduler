# Copyright 2025-2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Tests for SignupMethod enum."""

from shared.models.signup_method import SignupMethod


def test_signup_method_values():
    """Verify SignupMethod enum has correct string values."""
    assert SignupMethod.SELF_SIGNUP.value == "SELF_SIGNUP"
    assert SignupMethod.HOST_SELECTED.value == "HOST_SELECTED"


def test_signup_method_members():
    """Verify SignupMethod enum has exactly two members."""
    members = list(SignupMethod)
    assert len(members) == 2
    assert SignupMethod.SELF_SIGNUP in members
    assert SignupMethod.HOST_SELECTED in members


def test_signup_method_display_name():
    """Verify display_name property returns user-friendly names."""
    assert SignupMethod.SELF_SIGNUP.display_name == "Self Signup"
    assert SignupMethod.HOST_SELECTED.display_name == "Host Selected"


def test_signup_method_description():
    """Verify description property returns helpful descriptions."""
    self_signup_desc = SignupMethod.SELF_SIGNUP.description
    host_selected_desc = SignupMethod.HOST_SELECTED.description

    assert "join" in self_signup_desc.lower()
    assert "button" in self_signup_desc.lower()

    assert "host" in host_selected_desc.lower()
    assert "disabled" in host_selected_desc.lower()


def test_signup_method_string_usage():
    """Verify enum members can be used as strings."""
    assert isinstance(SignupMethod.SELF_SIGNUP, str)
    assert isinstance(SignupMethod.HOST_SELECTED, str)

    assert SignupMethod.SELF_SIGNUP == "SELF_SIGNUP"
    assert SignupMethod.HOST_SELECTED == "HOST_SELECTED"


def test_signup_method_string_comparison():
    """Verify enum values can be compared with strings."""
    method = SignupMethod.SELF_SIGNUP
    assert method == "SELF_SIGNUP"
    assert method != "HOST_SELECTED"

    method = SignupMethod.HOST_SELECTED
    assert method == "HOST_SELECTED"
    assert method != "SELF_SIGNUP"


def test_signup_method_can_be_stored_as_string():
    """Verify enum values work in contexts requiring strings."""
    methods_dict = {
        SignupMethod.SELF_SIGNUP: "Players can join",
        SignupMethod.HOST_SELECTED: "Host adds players",
    }

    assert methods_dict["SELF_SIGNUP"] == "Players can join"
    assert methods_dict["HOST_SELECTED"] == "Host adds players"
