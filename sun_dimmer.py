#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import geocoder
import subprocess
import time
import re
import os
import json
import signal
import sys
import argparse
from datetime import datetime
from pathlib import Path
from pysolar.solar import get_altitude

# --- Klasa do zarządzania kolorami w terminalu ---
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_MAGENTA = '\033[95m'

# --- KONFIGURACJA ---
CONFIG_FILE = Path.home() / '.config' / 'sun_dimmer' / 'config.json'
STATE_FILE = Path.home() / '.config' / 'sun_dimmer' / 'state.json'

# Domyślna konfiguracja
DEFAULT_CONFIG = {
    'location': {
        'manual_latitude': 52.3821038,
        'manual_longitude': 16.9141764,
        'use_auto_location': False
    },
    'brightness': {
        'min_brightness': 1,
        'max_brightness': 100,
        'sun_down_alt': -6,
        'sun_high_alt': 30,
        'manual_change_tolerance': 2
    },
    'system': {
        'update_interval': 300,
        'log_level': 'INFO',
        'log_before_change_minutes': 15 
    },
    'devices': [
        {'type': 'laptop', 'id': None, 'name': 'Ekran laptopa'},
        {'type': 'monitor', 'id': 1, 'name': 'Monitor Dell'}
    ]
}

class SunDimmer:
    def __init__(self, config_path=None):
        self.config_path = config_path or CONFIG_FILE
        self.state_path = STATE_FILE
        self.running = True
        self.last_logged_brightness = None
        self.enable_colors = True 
        
        # Załaduj konfigurację i stan po ustawieniu enable_colors
        self.config = self.load_config()
        self.state = self.load_state()
        
        # Obsługa sygnałów do czystego zamknięcia
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        self.log_message('INFO', "Otrzymano sygnał zakończenia, zapisuję stan...")
        self.save_state()
        self.running = False
        sys.exit(0)
    
    def colorize(self, text, color_code):
        """Dodaje kolory tylko jeśli terminal to obsługuje."""
        if self.enable_colors:
            return f"{color_code}{text}{Colors.RESET}"
        return text
        
    def load_config(self):
        """Ładuje konfigurację z pliku lub tworzy domyślną."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Dodaj nowe opcje jeśli nie istnieją
                if 'log_before_change_minutes' not in config.get('system', {}):
                    config.setdefault('system', {})['log_before_change_minutes'] = 15
                #self.log_message('SUCCESS', f"Załadowano konfigurację z {self.config_path}")
                return config
            except Exception as e:
                self.log_message('ERROR', f"Błąd ładowania konfiguracji: {e}")
        
        # Tworzenie domyślnego pliku konfiguracyjnego
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        self.log_message('INFO', f"Utworzono domyślną konfigurację w {self.config_path}")
        return DEFAULT_CONFIG.copy()
    
    def load_state(self):
        """Ładuje zapisany stan (offset, ostatnia jasność)."""
        if self.state_path.exists():
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                offset = state.get('user_offset', 0)
                if offset != 0:
                    offset_str = self.colorize(f"{int(offset):+d}%", f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}")
                    self.log_message('INFO', f"Przywrócono zapisany offset: {offset_str}")
                return state
            except Exception as e:
                self.log_message('ERROR', f"Błąd ładowania stanu: {e}")
        
        return {'user_offset': 0, 'last_brightness': 50}
    
    def save_state(self):
        """Zapisuje aktualny stan do pliku."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            self.log_message('ERROR', f"Błąd zapisywania stanu: {e}")

    def log_message(self, level, message):
        """Loguje wiadomość z odpowiednimi kolorami."""
        now = datetime.now().strftime('%H:%M:%S')
        timestamp = self.colorize(f"[{now}]", Colors.WHITE)
        
        level_map = {
            'INFO': {'tag': ' INFO  ', 'color': Colors.BLUE}, 
            'SUCCESS': {'tag': 'SUCCESS', 'color': Colors.GREEN},
            'WARN': {'tag': '  WARN ', 'color': Colors.YELLOW}, 
            'ERROR': {'tag': ' ERROR ', 'color': Colors.RED}
        }
        level_info = level_map.get(level.upper(), {'tag': '  LOG  ', 'color': Colors.WHITE})
        level_tag = self.colorize(f"[{level_info['tag']}]", f"{level_info['color']}{Colors.BOLD}")
        print(f"{timestamp} {level_tag} {message}")

    def should_log_now(self, current_brightness, next_brightness):
        """Sprawdza czy powinniśmy logować w tym momencie."""
        # Zawsze loguj błędy, ostrzeżenia i ważne zdarzenia
        return True
    
    def will_brightness_change_soon(self, lat, lon):
        """Sprawdza czy jasność zmieni się w ciągu następnych X minut."""
        try:
            log_minutes = self.config['system']['log_before_change_minutes']
            current_time = datetime.now().astimezone()
            future_time = datetime.fromtimestamp(current_time.timestamp() + log_minutes * 60).astimezone()
            
            current_altitude = get_altitude(lat, lon, current_time)
            future_altitude = get_altitude(lat, lon, future_time)
            
            current_brightness = self.calculate_brightness_from_sun(current_altitude) + self.state['user_offset']
            future_brightness = self.calculate_brightness_from_sun(future_altitude) + self.state['user_offset']
            
            # Sprawdź czy jasność zmieni się o więcej niż 1%
            return abs(future_brightness - current_brightness) > 1
        except:
            return True  # W przypadku błędu, loguj dla bezpieczeństwa

    def get_location(self):
        """Pobiera lokalizację zgodnie z konfiguracją."""
        if not self.config['location']['use_auto_location']:
            lat = self.config['location']['manual_latitude']
            lon = self.config['location']['manual_longitude']
            return lat, lon
            
        # Automatyczne wykrywanie lokalizacji
        self.log_message('INFO', "Próba ustalenia lokalizacji z GeoClue...")
        lat, lon = self.get_location_geoclue()
        
        if not lat:
            self.log_message('WARN', "GeoClue niedostępne. Próba z IP...")
            lat, lon = self.get_location_ip()
            
        return lat, lon

    def get_location_geoclue(self):
        try:
            result = subprocess.run(['/usr/lib/geoclue-2.0/demos/where-am-i'], 
                                  capture_output=True, text=True, timeout=15, check=True)
            lat_match = re.search(r'Latitude:\s*(-?\d+\.\d+)', result.stdout)
            lon_match = re.search(r'Longitude:\s*(-?\d+\.\d+)', result.stdout)
            if lat_match and lon_match:
                return float(lat_match.group(1)), float(lon_match.group(1))
        except:
            pass
        return None, None

    def get_location_ip(self):
        try:
            g = geocoder.ip('me')
            return g.latlng[0], g.latlng[1] if g.ok else (None, None)
        except:
            return None, None

    def get_sun_altitude(self, lat, lon):
        if lat is None or lon is None:
            return None
        return get_altitude(lat, lon, datetime.now().astimezone())

    def get_current_brightness(self):
        """Odczytuje aktualną jasność z pierwszego skonfigurowanego urządzenia."""
        devices = self.config['devices']
        if not devices:
            return None
            
        device = devices[0]
        try:
            if device['type'] == 'laptop':
                result = subprocess.run(['brightnessctl', 'info'], 
                                      capture_output=True, text=True, check=True)
                match = re.search(r'\((\d+)%\)', result.stdout)
                if match:
                    return int(match.group(1))
            
            elif device['type'] == 'monitor':
                result = subprocess.run(['ddcutil', '-d', str(device['id']), 'getvcp', '10'], 
                                      capture_output=True, text=True, check=True)
                match = re.search(r'current value =\s*(\d+)', result.stdout)
                if match:
                    return int(match.group(1))
        except Exception as e:
            self.log_message('ERROR', f"Nie można odczytać jasności z '{device['name']}': {e}")
        return None

    def set_brightness(self, percentage, should_log=True, altitude=None):
        """Ustawia nową jasność na wszystkich urządzeniach z listy."""
        brightness_config = self.config['brightness']
        percentage = max(brightness_config['min_brightness'], 
                        min(brightness_config['max_brightness'], int(percentage)))
        
        if should_log:
            value_str = self.colorize(f"{percentage}%", f"{Colors.BRIGHT_YELLOW}{Colors.BOLD}")
            alt_str = self.colorize(f"{altitude:.2f}°", f"{Colors.BRIGHT_CYAN}{Colors.BOLD}") if altitude is not None else ""
            offset_info = f" (offset: {int(self.state['user_offset']):+d}%)" if self.state['user_offset'] != 0 else ""
            sun_info = f" | Słońce: {alt_str}{offset_info}" if altitude is not None else ""
            self.log_message('INFO', f"Ustawiam jasność na {value_str}{sun_info}")

        success_flag = True
        for device in self.config['devices']:
            try:
                cmd = []
                if device['type'] == 'laptop':
                    cmd = ['brightnessctl', 'set', f'{percentage}%']
                elif device['type'] == 'monitor':
                    cmd = ['ddcutil', '-d', str(device['id']), 'setvcp', '10', str(percentage)]
                
                if cmd:
                    subprocess.run(cmd, check=True, capture_output=True, text=True)
            except Exception as e:
                if should_log:
                    self.log_message('ERROR', f"Błąd dla '{device['name']}': {e}")
                success_flag = False
                
        return percentage if success_flag else None

    def calculate_brightness_from_sun(self, altitude):
        """Oblicza jasność na podstawie wysokości słońca."""
        brightness_config = self.config['brightness']
        
        if altitude <= brightness_config['sun_down_alt']:
            return brightness_config['min_brightness']
        elif altitude >= brightness_config['sun_high_alt']:
            return brightness_config['max_brightness']
        else:
            sun_range = brightness_config['sun_high_alt'] - brightness_config['sun_down_alt']
            brightness_range = brightness_config['max_brightness'] - brightness_config['min_brightness']
            sun_progress = (altitude - brightness_config['sun_down_alt']) / sun_range
            return brightness_config['min_brightness'] + (sun_progress * brightness_range)

    def set_offset(self, new_offset):
        """Programowo ustawia nowy offset jasności."""
        old_offset = self.state['user_offset']
        self.state['user_offset'] = new_offset
        self.save_state()
        
        old_str = self.colorize(f"{int(old_offset):+d}%", f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}")
        new_str = self.colorize(f"{int(new_offset):+d}%", f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}")
        self.log_message('INFO', f"Zmieniono offset z {old_str} na {new_str}")
        
        return True

    def get_status(self):
        """Zwraca aktualny status programu."""
        return {
            'user_offset': self.state['user_offset'],
            'last_brightness': self.state['last_brightness'],
            'config_file': str(self.config_path),
            'state_file': str(self.state_path)
        }

    def run(self):
        """Główna pętla programu."""
        device_names = ', '.join([self.colorize(d['name'], Colors.BOLD) 
                                 for d in self.config['devices']])
        self.log_message('INFO', f"Kontrolowane urządzenia: {device_names}")

        lat, lon = self.get_location()
        if not lat:
            self.log_message('ERROR', "Nie udało się ustalić lokalizacji.")
            return
            
        location_str = self.colorize(f"({lat:.4f}, {lon:.4f})", Colors.BOLD)
        self.log_message('SUCCESS', f"Lokalizacja: {location_str}")

        last_set_brightness = self.get_current_brightness() or 50
        is_first_run = True

        while self.running:
            try:
                current_actual_brightness = self.get_current_brightness()
                altitude = self.get_sun_altitude(lat, lon)
                
                if altitude is None:
                    time.sleep(self.config['system']['update_interval'])
                    continue
                
                calculated_brightness = self.calculate_brightness_from_sun(altitude)
                
                # Sprawdź czy wkrótce nastąpi zmiana jasności
                should_log = self.will_brightness_change_soon(lat, lon)
                
                # Wykrywanie ręcznych zmian jasności
                if not is_first_run and current_actual_brightness is not None:
                    tolerance = self.config['brightness']['manual_change_tolerance']
                    if abs(current_actual_brightness - last_set_brightness) > tolerance:
                        new_offset = current_actual_brightness - calculated_brightness
                        offset_str = self.colorize(f"{int(new_offset):+d}%", f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}")
                        self.log_message('WARN', f"Wykryto ręczną zmianę! Nowy offset: {offset_str}")
                        self.set_offset(new_offset)

                final_brightness = calculated_brightness + self.state['user_offset']
                
                # Sprawdź czy jasność rzeczywiście się zmieni
                brightness_will_change = (self.last_logged_brightness is None or 
                                        abs(final_brightness - self.last_logged_brightness) > 0.5)
                
                # Ustaw jasność (loguj tylko jeśli to konieczne, przekaż altitude dla połączonego logu)
                newly_set_brightness = self.set_brightness(final_brightness, should_log and brightness_will_change, altitude)
                
                if newly_set_brightness is not None:
                    last_set_brightness = newly_set_brightness
                    self.state['last_brightness'] = newly_set_brightness
                    self.save_state()
                    
                    if brightness_will_change:
                        self.last_logged_brightness = final_brightness
                
                is_first_run = False
                
                time.sleep(self.config['system']['update_interval'])
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.log_message('ERROR', f"Nieoczekiwany błąd: {e}")
                time.sleep(60)  # Krótka przerwa przed ponowną próbą

def main():
    parser = argparse.ArgumentParser(description='Sun Dimmer - automatyczne dostosowywanie jasności')
    parser.add_argument('--config', help='Ścieżka do pliku konfiguracyjnego')
    parser.add_argument('--offset', type=int, help='Ustaw nowy offset jasności')
    parser.add_argument('--status', action='store_true', help='Pokaż aktualny status')
    parser.add_argument('--daemon', action='store_true', help='Uruchom w trybie demona')
    
    args = parser.parse_args()
    
    dimmer = SunDimmer(args.config)
    
    if args.status:
        status = dimmer.get_status()
        print(f"Aktualny offset: {status['user_offset']:+d}%")
        print(f"Ostatnia jasność: {status['last_brightness']}%")
        print(f"Plik konfiguracyjny: {status['config_file']}")
        print(f"Plik stanu: {status['state_file']}")
        return
    
    if args.offset is not None:
        if dimmer.set_offset(args.offset):
            print(f"Ustawiono nowy offset: {args.offset:+d}%")
        return
    
    if args.daemon:
        # Tutaj można dodać kod do uruchomienia jako demon systemowy
        pass
    
    dimmer.run()

if __name__ == "__main__":
    main()