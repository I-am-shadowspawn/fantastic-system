"""Exercise the actual diagnostics lambdas using native C++ and local state stubs."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class Loader(yaml.SafeLoader):
    pass


for tag in ('!lambda', '!extend'):
    Loader.add_constructor(tag, lambda loader, node: loader.construct_scalar(node))
CONFIG = yaml.load((ROOT / 'esphome/packages/device_info.yaml').read_text(), Loader=Loader)
SCRIPTS = {script['id']: script for script in CONFIG['script']}
HEATING = yaml.load((ROOT / 'esphome/packages/heating.yaml').read_text(), Loader=Loader)
HEATING_SCRIPTS = {script['id']: script for script in HEATING['script']}


class DeviceInfoTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('g++'), 'Requires a native C++ compiler')
    def test_persistence_sync_clock_changes_and_visible_views(self):
        declarations = [f"{g['type']} {g['id']} = {g.get('initial_value', '{}')};" for g in CONFIG['globals']]
        boot = CONFIG['esphome']['on_boot']['then'][0]['lambda']
        sync = CONFIG['time'][0]['on_time_sync'][0]['lambda']
        render = SCRIPTS['device_info_render']['then'][0]['lambda'].replace('${timezone}', 'Europe/London')
        close = SCRIPTS['device_overlay_close']['then'][0]['lambda']
        code = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <string>
#include <vector>
#define id(x) x
#define ESP_LOGW(...) ((void)0)
#define ESPHOME_VERSION "2026.11.0"
#define ESPHOME_PROJECT_VERSION "test-version"
uint64_t now_ms = 1000;
uint64_t millis_64() { return now_ms; }
struct Preferences {
  std::vector<unsigned char> bytes;
  bool writable = true;
  int writes = 0;
  template<class T> struct Object {
    Preferences *owner;
    bool load(T *out) { if(owner->bytes.size()!=sizeof(T)) return false; memcpy(out,owner->bytes.data(),sizeof(T)); return true; }
    bool save(T *in) { if(!owner->writable) return false; owner->bytes.resize(sizeof(T)); memcpy(owner->bytes.data(),in,sizeof(T)); ++owner->writes; return true; }
  };
  template<class T> Object<T> make_preference(uint32_t) { return {this}; }
  bool sync() { return writable; }
} preferences;
Preferences *global_preferences = &preferences;
uint32_t fnv1_hash(const char *p) { uint32_t h=2166136261; for(;*p;++p) h=(h^*p)*16777619; return h; }
struct Application { static constexpr size_t BUILD_TIME_STR_SIZE=26; };
struct AppType {
  uint32_t config=123;
  time_t build=1795350000;
  std::string name="ha-console";
  uint32_t get_config_version_hash() { return config; }
  time_t get_build_time() { return build; }
  const std::string &get_name() { return name; }
  void get_build_time_string(char *p) { strcpy(p,"2026-11-22 16:00:00 +0000"); }
} App;
struct Label { std::string text; bool hidden=false; };
using lv_obj_t=Label;
Label screen, other_screen;
Label build_storage, boot_storage, wifi_storage, values_storage, overlay_storage;
Label *info_build_values=&build_storage, *info_boot_values=&boot_storage, *info_wifi_values=&wifi_storage;
Label *device_overlay_values=&values_storage, *device_overlay=&overlay_storage;
struct Page { Label *obj; } info_page_storage{&screen};
Page *info_page=&info_page_storage;
Label *active_screen=&screen;
Label *lv_screen_active() { return active_screen; }
const char *lv_label_get_text(Label *label) { return label->text.c_str(); }
void lv_label_set_text(Label *label,const char *value) { label->text=value; }
void lv_obj_set_hidden(Label *label,bool hidden) { label->hidden=hidden; }
struct Sensor { float state=-65; bool has_state() { return true; } } wifi_rssi;
struct Text { std::string state; bool has_state() { return !state.empty(); } } device_wifi_ssid{"Test WiFi"},device_reset_reason{"task watchdog"};
struct WiFi { bool connected=true; bool is_connected() { return connected; } } wifi_component;
namespace wifi { WiFi *global_wifi_component=&wifi_component; }
struct Address { uint32_t addr=1; };
struct esp_netif_ip_info_t { Address ip,gw; };
using esp_netif_t=int;
esp_netif_t netif=0;
esp_netif_t *esp_netif_get_handle_from_ifkey(const char *) { return &netif; }
constexpr int ESP_OK=0;
int esp_netif_get_ip_info(esp_netif_t *,esp_netif_ip_info_t *) { return ESP_OK; }
namespace network {
constexpr size_t IP_ADDRESS_BUFFER_SIZE=40;
struct IPAddress { explicit IPAddress(Address *) {} char *str_to(char *buf) { strcpy(buf,"192.0.2.1"); return buf; } };
}
struct ESPTime {
  time_t timestamp=0;
  bool is_valid() { return timestamp>=1546300800; }
  static ESPTime from_epoch_local(time_t t) { return {t}; }
  std::string strftime(const char *format) { char buf[120]; auto tm=*std::gmtime(&timestamp); std::strftime(buf,sizeof(buf),format,&tm); return buf; }
};
struct Clock { time_t epoch=1795350000; ESPTime now() { return {epoch}; } } ha_time;
bool heating_ota_active=false;
std::vector<std::string> heating_ha_clients{"ha"};
DECLARATIONS
void boot() { BOOT }
void synced() { SYNC }
void render() { RENDER }
void close_overlay() { CLOSE }
int main() {
  boot(); assert(device_boot_count==1 && device_boot_count_saved && preferences.writes==1);
  boot(); assert(device_boot_count==2 && preferences.writes==2);
  App.build++; boot(); assert(device_boot_count==1);
  App.config++; boot(); assert(device_boot_count==1);
  preferences.writable=false; boot(); assert(device_boot_count==2 && !device_boot_count_saved);
  preferences.writable=true; boot(); assert(device_boot_count==2);
  int writes=preferences.writes;
  render();
  assert(info_build_values->text.find("test-version")!=std::string::npos);
  assert(info_boot_values->text.find("task watchdog")!=std::string::npos);
  assert(info_boot_values->text.find("Boots this build: 2")!=std::string::npos);
  assert(info_wifi_values->text.find("Test WiFi")!=std::string::npos);
  assert(info_wifi_values->text.find("-65 dBm (Good)")!=std::string::npos);
  device_reset_reason.state="power-on event"; render();
  assert(info_boot_values->text.find("Power-on")!=std::string::npos);
  device_reset_reason.state="Reboot request from restart.button"; render();
  assert(info_boot_values->text.find("Manual restart request")!=std::string::npos);
  device_reset_reason.state="software via esp_restart"; render();
  assert(info_boot_values->text.find("source unknown")!=std::string::npos);
  // Hidden pages are not rewritten; rendering does not write preferences.
  active_screen=&other_screen;
  info_boot_values->text="unchanged"; now_ms+=2000; render();
  assert(info_boot_values->text=="unchanged" && preferences.writes==writes);
  device_overlay_mode=2; ha_time.epoch=0; render();
  assert(device_overlay_values->text.find("Waiting for Home Assistant time")!=std::string::npos);
  assert(device_overlay_values->text.find("Not synchronized this boot")!=std::string::npos);
  synced(); assert(!device_time_synced);
  ha_time.epoch=1795350000; synced(); assert(device_time_synced);
  now_ms+=60000; ha_time.epoch-=3600; render();
  assert(device_overlay_values->text.find("Since sync: 0d 00:01:00")!=std::string::npos);
  // A successful re-sync resets age even when no correction was needed.
  synced(); render(); assert(device_overlay_values->text.find("Since sync: 0d 00:00:00")!=std::string::npos);
  now_ms+=(uint64_t(1)<<32)+1000; render();
  assert(device_overlay_values->text.find("Since sync: 49d")!=std::string::npos);
  device_overlay_mode=1; wifi_component.connected=false; heating_ha_clients.clear(); render();
  assert(device_overlay_values->text.find("Wi-Fi: Disconnected")!=std::string::npos);
  assert(device_overlay_values->text.find("IP: --")!=std::string::npos);
  assert(device_overlay_values->text.find("Signal: --")!=std::string::npos);
  assert(device_overlay_values->text.find("HA API: Disconnected")!=std::string::npos);
  heating_ota_active=true; device_overlay_values->text="unchanged"; render();
  assert(device_overlay_values->text=="unchanged");
  close_overlay(); assert(device_overlay_mode==0 && device_overlay->hidden && active_screen==&other_screen);
  uint32_t maximum=UINT32_MAX; memcpy(preferences.bytes.data()+4,&maximum,sizeof(maximum));
  boot(); assert(device_boot_count==UINT32_MAX);
  uint32_t invalid_format=99; memcpy(preferences.bytes.data(),&invalid_format,sizeof(invalid_format));
  boot(); assert(device_boot_count==1);
}
'''
        for key, value in {'DECLARATIONS': '\n'.join(declarations), 'BOOT': boot, 'SYNC': sync,
                           'RENDER': render, 'CLOSE': close}.items():
            code = code.replace(key, value)
        with tempfile.TemporaryDirectory(prefix='device-info-test-') as folder:
            source, binary = Path(folder)/'test.cpp', Path(folder)/'test'
            source.write_text(code)
            result = subprocess.run(['g++', '-std=c++17', str(source), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('g++'), 'Requires a native C++ compiler')
    def test_heating_indicator_transitions_and_battery_boundaries(self):
        render = HEATING_SCRIPTS['heating_render']['then'][0]['lambda']
        body = 'const bool state_known' + render.split('const bool state_known', 1)[1].split('set_enabled(c->target_button', 1)[0]
        create_label = 'auto label =' + render.split('auto label =', 1)[1].split('const int button_height', 1)[0]
        code = r'''
#include <cassert>
#include <cmath>
#include <cstdio>
#include <map>
#include <string>
#include <variant>
struct Field {
  std::variant<std::monostate,float,bool,std::string> value;
  template<class T> bool is() const { return std::holds_alternative<T>(value); }
  template<class T> T as() const { return std::get<T>(value); }
  bool operator|(bool fallback) const { return is<bool>() ? as<bool>() : fallback; }
  const char *operator|(const char *fallback) const { return is<std::string>() ? std::get<std::string>(value).c_str() : fallback; }
};
using Item=std::map<std::string,Field>;
struct Label { unsigned state=0,color=0,opacity=0; bool hidden=false; std::string text; };
using lv_obj_t=Label;
constexpr int LV_OPA_COVER=255,LV_TEXT_ALIGN_CENTER=0,LV_LABEL_LONG_DOT=0;
int lv_pct(int x) { return x; }
Label *lv_label_create(Label *) { return new Label{}; }
void lv_obj_set_width(Label *,int) {}
void lv_obj_set_style_text_align(Label *,int,int) {}
void lv_label_set_long_mode(Label *,int) {}
void lv_obj_set_style_text_opa(Label *label,unsigned value,int) { label->opacity=value; }
struct Card { Label *boost_button,*flame,*battery_label; };
constexpr unsigned LV_STATE_CHECKED=1;
void lv_obj_add_state(Label *o,unsigned state) { o->state|=state; }
void lv_obj_remove_state(Label *o,unsigned state) { o->state&=~state; }
void lv_obj_set_hidden(Label *o,bool value) { o->hidden=value; }
void lv_label_set_text(Label *o,const char *s) { o->text=s; }
template<class... Args> void lv_label_set_text_fmt(Label *o,const char *f,Args... args) { char text[80]; snprintf(text,sizeof(text),f,args...); o->text=text; }
unsigned lv_color_hex(unsigned color) { return color; }
void lv_obj_set_style_text_color(Label *o,unsigned color,int) { o->color=color; }
void apply(Card *c,Item &item,bool fresh) { BODY }
int main() {
  Label boost,flame,battery; Card card{&boost,&flame,&battery};
  Item item{{"kind",Field{std::string("room")}}, {"available",Field{true}},
            {"boosted",Field{true}}, {"heating",Field{true}}, {"battery_percent",Field{30.0f}}};
  apply(&card,item,true);
  assert(boost.state==LV_STATE_CHECKED && !flame.hidden && !battery.hidden);
  assert(battery.text.find("30%")!=std::string::npos && battery.color==0x7ED321);
  // Reproduce a black-text header/footer theme: the actual label factory must
  // set a readable colour and opacity on the label itself, not just its parent.
  CREATE_LABEL
  Label black_parent;
  auto *title=label(&black_parent); auto *status=label(&black_parent);
  assert(title->color==0xFFFFFF && title->opacity==LV_OPA_COVER);
  assert(status->color==0xFFFFFF && status->opacity==LV_OPA_COVER);
  delete title; delete status;
  item["boosted"].value=false; item["heating"].value=false;
  float levels[]={0,15,15.5f,16,24,25,25.5f,26,50,51,75,76,100};
  const char *glyphs[]={"\uF244","\uF243","\uF243","\uF243","\uF243","\uF243","\uF242","\uF242","\uF242","\uF241","\uF241","\uF240","\uF240"};
  for(int i=0;i<13;++i) {
    item["battery_percent"].value=levels[i]; apply(&card,item,true);
    assert(battery.text.rfind(glyphs[i],0)==0);
    assert(battery.color==(levels[i]<=15 ? 0xFF6B6B : levels[i]<=25 ? 0xFFC107 : 0x7ED321));
    assert(boost.state==0 && flame.hidden);
  }
  item["boosted"].value=true; item["heating"].value=true;
  apply(&card,item,false);
  assert(boost.state==0 && flame.hidden && battery.text.find("--")!=std::string::npos && battery.color==0x64B5F6);
  item.erase("battery_percent"); apply(&card,item,true);
  assert(!battery.hidden && battery.text.find("--")!=std::string::npos && battery.color==0x64B5F6);
  item["kind"].value=std::string("hot_water"); apply(&card,item,true); assert(battery.hidden);
  item["kind"].value=std::string("room");
  for(float invalid : {-1.0f,101.0f,NAN}) {
    item["battery_percent"].value=invalid; apply(&card,item,true);
    assert(battery.text.find("--")!=std::string::npos && battery.color==0x64B5F6);
  }
}
'''.replace('BODY', body).replace('CREATE_LABEL', create_label)
        with tempfile.TemporaryDirectory(prefix='heating-indicators-') as directory:
            source, binary = Path(directory)/'test.cpp', Path(directory)/'test'
            source.write_text(code)
            result = subprocess.run(['g++', '-std=c++17', str(source), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
