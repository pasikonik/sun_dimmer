# Sun Dimmer

Sun Dimmer is a Python script that automatically adjusts the brightness of your screen(s) based on the position of the sun. It calculates the sun's altitude at your location and adjusts the brightness accordingly, ensuring a comfortable viewing experience throughout the day.

## Features

- **Automatic Brightness Adjustment**: Dynamically adjusts screen brightness based on the sun's altitude.
- **Manual Offset**: Allows users to manually adjust brightness offset.
- **Multi-Device Support**: Supports both laptop screens and external monitors.
- **Customizable Configuration**: Easily configurable via a JSON file.
- **Location Detection**: Supports both manual and automatic location detection (via GeoClue or IP-based geolocation).
- **Logging**: Provides detailed logs with color-coded messages for better readability.

## Requirements

- Python 3.6 or higher
- Dependencies:
  - `pysolar`
  - `geocoder`
- External tools:
  - `brightnessctl` (for laptop screen brightness control)
  - `ddcutil` (for external monitor brightness control)
  - `GeoClue` (optional, for automatic location detection)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/sun_dimmer.git
   cd sun_dimmer
   ```

2. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure the required external tools (`brightnessctl`, `ddcutil`, `GeoClue`) are installed on your system.

## Usage

Run the script with the following command:
```bash
python3 sun_dimmer.py
```

### Command-Line Options

- `--config`: Specify a custom configuration file path.
- `--offset`: Set a manual brightness offset (e.g., `--offset 10` to increase brightness by 10%).
- `--status`: Display the current status, including offset, last brightness, and file paths.
- `--daemon`: Run the script as a daemon (not implemented yet).

### Example Commands

- Display the current status:
  ```bash
  python3 sun_dimmer.py --status
  ```

- Set a manual brightness offset:
  ```bash
  python3 sun_dimmer.py --offset 15
  ```

## Configuration

The configuration file is located at `~/.config/sun_dimmer/config.json` by default. It is automatically created with default values if it does not exist. Below is an example configuration:

```json
{
  "location": {
    "manual_latitude": 52.3821038,
    "manual_longitude": 16.9141764,
    "use_auto_location": false
  },
  "brightness": {
    "min_brightness": 1,
    "max_brightness": 100,
    "sun_down_alt": -6,
    "sun_high_alt": 30,
    "manual_change_tolerance": 2
  },
  "system": {
    "update_interval": 300,
    "log_level": "INFO",
    "log_before_change_minutes": 15
  },
  "devices": [
    {"type": "laptop", "id": null, "name": "Ekran laptopa"},
    {"type": "monitor", "id": 1, "name": "Monitor Dell"}
  ]
}
```

### Key Configuration Options

- **Location**:
  - `manual_latitude` and `manual_longitude`: Coordinates for manual location.
  - `use_auto_location`: Set to `true` to enable automatic location detection.

- **Brightness**:
  - `min_brightness` and `max_brightness`: Define the brightness range.
  - `sun_down_alt` and `sun_high_alt`: Define the sun altitude range for brightness adjustment.

- **System**:
  - `update_interval`: Time (in seconds) between brightness updates.
  - `log_level`: Logging level (`INFO`, `WARN`, `ERROR`).
  - `log_before_change_minutes`: Time (in minutes) to log before a significant brightness change.

- **Devices**:
  - Define the devices to control. Each device can be of type `laptop` or `monitor`.

## State File

The state file is located at `~/.config/sun_dimmer/state.json` by default. It stores the current brightness offset and the last set brightness.

## Logging

The script logs messages with the following levels:
- `INFO`: General information.
- `SUCCESS`: Successful operations.
- `WARN`: Warnings, such as fallback to manual location.
- `ERROR`: Errors encountered during execution.

## Troubleshooting

- **Brightness Not Changing**:
  - Ensure `brightnessctl` and `ddcutil` are installed and properly configured.
  - Check if the devices are correctly defined in the configuration file.

- **Location Detection Fails**:
  - Ensure `GeoClue` is installed and running.
  - Use manual location as a fallback.

- **Permission Issues**:
  - Some operations may require elevated permissions. Run the script with `sudo` if necessary.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [pysolar](https://github.com/pingswept/pysolar) for solar altitude calculations.
- [geocoder](https://github.com/DenisCarriere/geocoder) for IP-based geolocation.
- [brightnessctl](https://github.com/Hummer12007/brightnessctl) and [ddcutil](https://www.ddcutil.com/) for brightness control.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests to improve the project.

---

Enjoy using Sun Dimmer!