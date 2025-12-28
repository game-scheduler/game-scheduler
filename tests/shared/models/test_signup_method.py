# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


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
