from lib.GazoToolsGUI import calculate_thumbnail_tile_size


def test_thumbnail_tile_size_stays_fixed_when_window_changes():
    width, height = calculate_thumbnail_tile_size(
        canvas_width=1200,
        canvas_height=900,
        rows=3,
        columns=4,
        base_width=160,
        base_height=160,
    )

    assert (width, height) == (160, 160)


def test_thumbnail_tile_size_uses_base_size_before_layout():
    assert calculate_thumbnail_tile_size(1, 1, 3, 4, 160, 120) == (160, 120)