"""
Regression tests for the sun-based timelapse recording window.

The window is computed from astral and then compared against a naive local
datetime.now(), so both the timezone the events are resolved in and the
conversion back to local time have to be right. Two bugs have lived here:

  1. stripping tzinfo without converting (shifted the window by the UTC offset)
  2. asking astral for a UTC day, which west of Greenwich returns the *previous*
     local evening's sunset — stretching sunset->sunrise to ~34h so the writer
     considered itself permanently in-window and recorded around the clock.

These assert on window *duration and ordering*, not on exact clock times, so
they stay valid wherever the suite runs.
"""

from datetime import date, timedelta

import pytest

from services.timelapse_writer import TimelapseWriter

pytest.importorskip('astral')

# A late-summer night at mid-northern latitude: long enough after the solstice
# that all four modes produce a real window, and far enough west that a
# UTC-vs-local day mixup shows up as a whole extra day.
NIGHT = date(2026, 8, 18)

LOCATIONS = [
    pytest.param(41.88, -87.63, id="chicago"),
    pytest.param(32.78, -96.80, id="dallas"),
    # East of Greenwich, where a UTC-day mixup would skew the other way.
    pytest.param(51.51, -0.13, id="london"),
    pytest.param(-33.87, 151.21, id="sydney"),
]

MODES = ['sunset_sunrise', 'civil', 'nautical', 'astronomical']


def _window(lat, lon, mode, day=NIGHT):
    w = TimelapseWriter()
    w._config = {
        'window_mode': 'sun',
        'sun_mode': mode,
        'sun_latitude': lat,
        'sun_longitude': lon,
        'fixed_start': '18:00',
        'fixed_end': '06:00',
    }
    return w._get_window_for_day(day)


@pytest.mark.parametrize("lat,lon", LOCATIONS)
@pytest.mark.parametrize("mode", MODES)
def test_sun_window_is_a_single_night(lat, lon, mode):
    """A night window must be one night long, not ~34h.

    Guards the UTC-day regression: taking sunset from astral's UTC day at a
    western longitude yields the previous evening, which made the window span
    two nights and left the writer permanently in-window.
    """
    start, end = _window(lat, lon, mode)
    hours = (end - start).total_seconds() / 3600
    assert 0 < hours < 20, (
        f"{mode} at {lat},{lon} produced a {hours:.1f}h window "
        f"({start} -> {end}); a single night is expected"
    )


@pytest.mark.parametrize("lat,lon", LOCATIONS)
@pytest.mark.parametrize("mode", MODES)
def test_sun_window_starts_on_the_requested_night(lat, lon, mode):
    """The window must open on the evening of the day asked for."""
    start, end = _window(lat, lon, mode)
    assert start.date() == NIGHT, (
        f"{mode} at {lat},{lon} opened on {start.date()}, expected {NIGHT}"
    )
    assert end > start
    assert end.date() <= NIGHT + timedelta(days=1)


@pytest.mark.parametrize("lat,lon", LOCATIONS)
def test_darker_thresholds_give_shorter_windows(lat, lon):
    """sunset/sunrise ⊃ civil ⊃ nautical ⊃ astronomical.

    Each successively darker sun elevation must start later and end earlier;
    if a conversion is wrong for one mode this ordering breaks.
    """
    windows = {m: _window(lat, lon, m) for m in MODES}
    for outer, inner in zip(MODES, MODES[1:]):
        o_start, o_end = windows[outer]
        i_start, i_end = windows[inner]
        assert i_start > o_start, f"{inner} should start after {outer} at {lat},{lon}"
        assert i_end < o_end, f"{inner} should end before {outer} at {lat},{lon}"


def test_missing_coordinates_fall_back_to_fixed_window():
    """Sun mode without coordinates must degrade to the fixed window.

    The controller feeds these from the weather location, which is blank until
    the user fills it in; silently recording nothing would be worse.
    """
    w = TimelapseWriter()
    w._config = {
        'window_mode': 'sun',
        'sun_mode': 'astronomical',
        'sun_latitude': None,
        'sun_longitude': None,
        'fixed_start': '18:00',
        'fixed_end': '06:00',
    }
    start, end = w._get_window_for_day(NIGHT)
    assert (start.hour, start.minute) == (18, 0)
    assert (end.hour, end.minute) == (6, 0)
    assert (end - start) == timedelta(hours=12)
