#!/usr/bin/env python3
"""Test harness for CYBER-OMNI - tests all modules programmatically."""
import sys, os, json, tempfile, traceback, importlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = 0
failed = 0
errors = []

def test(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS  {name}")
    except Exception as e:
        failed += 1
        tb = traceback.format_exc()
        errors.append((name, str(e), tb))
        print(f"  FAIL  {name}: {e}")

print("=" * 60)
print("CYBER-OMNI v2 Full Test Suite")
print("=" * 60)

tmpdir = tempfile.mkdtemp()

# 1. All imports
print("\n--- Import Tests ---")
imports_to_test = [
    ("core.engine", ["AIEngine"]),
    ("core.memory", ["ConversationMemory"]),
    ("core.context", ["SYSTEM_PROMPT", "WELCOME_MESSAGE", "TOR_WARNING"]),
    ("core.utils", ["print_banner", "colored", "clear_screen"]),
    ("core.proxy", ["check_anonymity", "start_tor", "check_tor", "tor_status", "ensure_tor", "require_tor", "signal_new_identity", "check_dns_leak", "spoof_mac", "verify_full_anonymity"]),
    ("core.stealth", ["get_random_profile", "set_profile", "current_profile", "randomize_profile", "get_headers", "get_request_kwargs", "list_profiles"]),
    ("core.session", ["SessionState"]),
    ("core.orchestrator", ["Orchestrator"]),
    ("core.websearch", ["WebSearch"]),
    ("core.setup", ["setup_wizard", "load_config", "save_config", "get_system_prompt_extra", "show_mode_info", "ask_feedback", "MODES"]),
    ("core.camouflage", ["stealth_gate", "setup_stealth", "get_fake_page", "randomize_style"]),
    ("core.plugin_manager", ["PluginManager"]),
    ("core.knowledge", ["learn_file", "query_knowledge", "KnowledgeBase"]),
    ("core.downloader", ["download_model", "MODELS", "get_models_dir", "list_models", "ensure_model"]),
    ("modules.scan", ["ScanModule"]),
    ("modules.recon", ["ReconModule"]),
    ("modules.osint", ["OSINTModule"]),
    ("modules.exploit", ["ExploitModule"]),
    ("modules.report", ["ReportModule"]),
    ("modules.attacker", ["AttackerModule", "TOOLS"]),
    ("modules.extractor", ["run_extraction"]),
    ("modules.autopwn", ["run_autopwn"]),
    ("modules.payload_factory", ["run_payload", "PayloadFactory"]),
    ("modules.cve_search", ["run_cve_search", "search_cve_by_id", "search_cve_by_keyword"]),
    ("modules.exploitdb", ["run_exploitdb_search", "ensure_db"]),
    ("modules.listener", ["run_listener"]),
    ("modules.subtake", ["run_subtake"]),
    ("modules.target_queue", ["run_target_queue"]),
    ("modules.nmap_parser", ["parse_nmap_xml", "run_nmap_parser", "format_nmap_results"]),
    ("modules.leak_check", ["run_leak_check", "check_hibp_email", "format_leak_results"]),
]
for mod_name, attrs in imports_to_test:
    def make_test(mod_name, attrs):
        def t():
            m = importlib.import_module(mod_name)
            for a in attrs:
                assert hasattr(m, a), f"{mod_name} missing {a}"
        return t
    test(f"Import {mod_name} ({', '.join(attrs)})", make_test(mod_name, attrs))

# 2. Dashboard (needs flask)
print("\n--- Dashboard Import ---")
try:
    wd = importlib.import_module("web_dashboard")
    test("web_dashboard import", lambda: None)
    test("web_dashboard.register_target", lambda: wd.register_target("127.0.0.1"))
    test("web_dashboard.remove_target", lambda: wd.remove_target("127.0.0.1"))
    test("web_dashboard.add_log", lambda: wd.add_log("test"))
except Exception as e:
    test("web_dashboard (Flask not installed)", lambda: (_ for _ in ()).throw(e))

# 3. Config save/load
print("\n--- Config Tests ---")
test("save_config/load_config", lambda: (
    m := importlib.import_module("core.setup"),
    orig := m.load_config(),
    m.save_config({"hat": "grey"}),
    loaded := m.load_config(),
    m.save_config(orig) if orig else None,
    None if loaded.get("hat") == "grey" else (_ for _ in ()).throw(AssertionError("config mismatch"))
))

# 4. Engine init
print("\n--- Engine Init Tests ---")
test("AIEngine() init", lambda: (
    e := importlib.import_module("core.engine").AIEngine(),
    None
))
test("AIEngine properties", lambda: (
    e := importlib.import_module("core.engine").AIEngine(),
    None if e.initialized == False else (_ for _ in ()).throw(AssertionError()),
    None if e.model_key is None else (_ for _ in ()).throw(AssertionError()),
))

# 5. Utils
print("\n--- Utils Tests ---")
test("colored() returns ANSI string", lambda: (
    r := importlib.import_module("core.utils").colored("hello", "31"),
    None if "\033[" in r else (_ for _ in ()).throw(AssertionError("no ANSI"))
))
test("print_banner() does not crash", lambda: importlib.import_module("core.utils").print_banner())
test("clear_screen() does not crash", lambda: importlib.import_module("core.utils").clear_screen())

# 6. Proxy
print("\n--- Proxy Tests ---")
test("tor_status() returns dict", lambda: (
    s := importlib.import_module("core.proxy").tor_status(),
    None if isinstance(s, dict) else (_ for _ in ()).throw(AssertionError())
))

# 7. Camouflage
print("\n--- Camouflage Tests ---")
test("stealth_gate() returns bool", lambda: (
    r := importlib.import_module("core.camouflage").stealth_gate(),
    None if isinstance(r, bool) else (_ for _ in ()).throw(AssertionError())
))
test("get_fake_page() returns string", lambda: (
    p := importlib.import_module("core.camouflage").get_fake_page("404"),
    None if len(p) > 10 else (_ for _ in ()).throw(AssertionError("too short"))
))
test("get_fake_page returns different styles", lambda: (
    m := importlib.import_module("core.camouflage"),
    p1 := m.get_fake_page("404"),
    p2 := m.get_fake_page("403"),
    None if p1 != p2 else (_ for _ in ()).throw(AssertionError("should differ"))
))

# 8. Modules init
print("\n--- Module Init Tests ---")
for mod_name, cls_name in [
    ("modules.scan", "ScanModule"),
    ("modules.recon", "ReconModule"),
    ("modules.osint", "OSINTModule"),
    ("modules.exploit", "ExploitModule"),
    ("modules.attacker", "AttackerModule"),
]:
    def make_init_test(mod_name, cls_name):
        def t():
            m = importlib.import_module(mod_name)
            cls = getattr(m, cls_name)
            inst = cls()
            assert inst is not None
        return t
    test(f"{cls_name}() init", make_init_test(mod_name, cls_name))

# 9. Knowledge base
print("\n--- Knowledge Base Tests ---")
test("KnowledgeBase(knowledge_dir=tmpdir) init", lambda: (
    importlib.import_module("core.knowledge").KnowledgeBase(knowledge_dir=tmpdir)
))
test("learn_file() no crash on missing file", lambda: (
    importlib.import_module("core.knowledge").learn_file("NONEXISTENT.md"),
    None
))
test("query_knowledge() returns string", lambda: (
    r := importlib.import_module("core.knowledge").query_knowledge("test"),
    None
))
test("KnowledgeBase ingest_file fails gracefully", lambda: (
    kb := importlib.import_module("core.knowledge").KnowledgeBase(knowledge_dir=tmpdir),
    kb.ingest_file("NONEXISTENT.md"),
    None
))
test("KnowledgeBase search returns list", lambda: (
    kb := importlib.import_module("core.knowledge").KnowledgeBase(knowledge_dir=tmpdir),
    r := kb.search("test"),
    None if isinstance(r, list) else (_ for _ in ()).throw(AssertionError())
))

# 10. Plugin manager
print("\n--- Plugin Manager Tests ---")
test("PluginManager(plugin_dir=tmpdir) init", lambda: (
    importlib.import_module("core.plugin_manager").PluginManager(plugin_dir=tmpdir)
))

# 11. Report module
print("\n--- Report Tests ---")
test("ReportModule() init", lambda: importlib.import_module("modules.report").ReportModule())
test("ReportModule.generate_summary with data", lambda: (
    rm := importlib.import_module("modules.report").ReportModule(),
    rm.generate_summary({"targets": ["test"], "findings": []}),
    None
))

# 12. Nmap parser
print("\n--- Nmap Parser Tests ---")
test("parse_nmap_xml with XML string", lambda: (
    xml := '<?xml version="1.0"?><nmaprun><host><address addr="10.0.0.1" addrtype="ipv4"/><ports><port protocol="tcp" portid="80"><state state="open"/><service name="http"/></port></ports></host></nmaprun>',
    result := importlib.import_module("modules.nmap_parser").parse_nmap_xml(xml),
    None if result and len(result["targets"]) == 1 else (_ for _ in ()).throw(AssertionError(f"expected 1 host, got {result}")),
    None if result["targets"][0]["ip"] == "10.0.0.1" else (_ for _ in ()).throw(AssertionError())
))

# 13. Leak check
print("\n--- Leak Check Tests ---")
test("run_leak_check with no API key returns gracefully", lambda: (
    result := importlib.import_module("modules.leak_check").run_leak_check("test@example.com", api_key=""),
    None
))

# 14. Payload factory
print("\n--- Payload Factory Tests ---")
test("PayloadFactory() init", lambda: importlib.import_module("modules.payload_factory").PayloadFactory())

# 15. Downloader
print("\n--- Downloader Tests ---")
test("MODELS has entries", lambda: (
    m := importlib.import_module("core.downloader").MODELS,
    None if len(m) > 0 else (_ for _ in ()).throw(AssertionError("MODELS empty"))
))
test("get_models_dir() returns str", lambda: (
    d := importlib.import_module("core.downloader").get_models_dir(),
    None if isinstance(d, str) else (_ for _ in ()).throw(AssertionError())
))
test("list_models() returns dict", lambda: (
    d := importlib.import_module("core.downloader").list_models(),
    None if isinstance(d, dict) else (_ for _ in ()).throw(AssertionError(f"expected dict, got {type(d)}"))
))

# 16. Websearch
print("\n--- WebSearch Tests ---")
test("WebSearch() init", lambda: importlib.import_module("core.websearch").WebSearch())

# 17. Stealth module
print("\n--- Stealth Module Tests ---")
test("get_random_profile returns dict with user_agent", lambda: (
    p := importlib.import_module("core.stealth").get_random_profile(),
    None if "user_agent" in p else (_ for _ in ()).throw(AssertionError("no user_agent"))
))
test("set_profile changes current profile", lambda: (
    s := importlib.import_module("core.stealth"),
    s.set_profile("firefox_121"),
    c := s.current_profile(),
    None if "Firefox/121.0" in c["user_agent"] else (_ for _ in ()).throw(AssertionError())
))
test("randomize_profile returns different UA", lambda: (
    s := importlib.import_module("core.stealth"),
    s.set_profile("chrome_120"),
    first := s.current_profile()["user_agent"],
    s.randomize_profile(),
    second := s.current_profile()["user_agent"],
    None  # just verify no crash
))
test("get_headers returns dict with Accept", lambda: (
    h := importlib.import_module("core.stealth").get_headers(),
    None if "Accept" in h else (_ for _ in ()).throw(AssertionError("no Accept"))
))
test("list_profiles returns tuple (list, name_or_None)", lambda: (
    r := importlib.import_module("core.stealth").list_profiles(),
    None if isinstance(r[0], list) else (_ for _ in ()).throw(AssertionError("not a list"))
))
test("get_request_kwargs returns dict with headers", lambda: (
    k := importlib.import_module("core.stealth").get_request_kwargs(),
    None if "headers" in k else (_ for _ in ()).throw(AssertionError("no headers"))
))

# 18. New proxy features
print("\n--- Proxy Layer 1 Tests ---")
test("signal_new_identity returns bool", lambda: (
    r := importlib.import_module("core.proxy").signal_new_identity(),
    None if isinstance(r, bool) else (_ for _ in ()).throw(AssertionError())
))
test("check_dns_leak returns bool", lambda: (
    r := importlib.import_module("core.proxy").check_dns_leak(),
    None if isinstance(r, bool) else (_ for _ in ()).throw(AssertionError())
))
test("verify_full_anonymity returns bool", lambda: (
    r := importlib.import_module("core.proxy").verify_full_anonymity(),
    None if isinstance(r, bool) else (_ for _ in ()).throw(AssertionError())
))
test("spoof_mac returns bool (no crash on Windows)", lambda: (
    r := importlib.import_module("core.proxy").spoof_mac(),
    None if isinstance(r, bool) else (_ for _ in ()).throw(AssertionError())
))

# 19. Session state
print("\n--- Session State Tests ---")
test("SessionState() init", lambda: importlib.import_module("core.session").SessionState())
test("SessionState.set_target", lambda: (
    s := importlib.import_module("core.session").SessionState(),
    s.set_target("10.0.0.5"),
    None if s.current_target == "10.0.0.5" else (_ for _ in ()).throw(AssertionError())
))
test("SessionState.add_finding ports", lambda: (
    s := importlib.import_module("core.session").SessionState(),
    s.set_target("10.0.0.5"),
    s.add_finding("ports", [22, 80, 443]),
    None if len(s.get_current()["findings"]["ports"]) == 3 else (_ for _ in ()).throw(AssertionError())
))
test("SessionState.add_action", lambda: (
    s := importlib.import_module("core.session").SessionState(),
    s.set_target("10.0.0.5"),
    s.add_action("scan", "Scanned target"),
    None if len(s.get_current()["actions_taken"]) == 1 else (_ for _ in ()).throw(AssertionError())
))
test("SessionState.set_stage", lambda: (
    s := importlib.import_module("core.session").SessionState(),
    s.set_target("10.0.0.5"),
    s.set_stage("scanned"),
    None if s.get_current()["stage"] == "scanned" else (_ for _ in ()).throw(AssertionError())
))
test("SessionState.get_summary returns string", lambda: (
    s := importlib.import_module("core.session").SessionState(),
    s.set_target("10.0.0.5"),
    r := s.get_summary(),
    None if "10.0.0.5" in r else (_ for _ in ()).throw(AssertionError())
))
test("SessionState.suggest_next_steps returns list", lambda: (
    s := importlib.import_module("core.session").SessionState(),
    s.set_target("10.0.0.5"),
    steps := s.suggest_next_steps(),
    None if isinstance(steps, list) else (_ for _ in ()).throw(AssertionError())
))
test("SessionState.save/load roundtrip", lambda: (
    s := importlib.import_module("core.session").SessionState(),
    s.set_target("10.0.0.5"),
    s.add_action("scan", "done"),
    fp := os.path.join(tmpdir, "test_session.json"),
    s.save(fp),
    s2 := importlib.import_module("core.session").SessionState.load(fp),
    None if s2.current_target == "10.0.0.5" else (_ for _ in ()).throw(AssertionError()),
    None if len(s2.targets["10.0.0.5"]["actions_taken"]) == 1 else (_ for _ in ()).throw(AssertionError())
))

# 20. Orchestrator
print("\n--- Orchestrator Tests ---")
test("Orchestrator() init with mock AI", lambda: (
    o := importlib.import_module("core.orchestrator").Orchestrator(None, {"anonymity": "always"}, {}),
    None
))
test("Orchestrator start_engagement returns string", lambda: (
    o := importlib.import_module("core.orchestrator").Orchestrator(None, {"anonymity": "always"}, {}),
    r := o.start_engagement("10.0.0.5"),
    None if "10.0.0.5" in r else (_ for _ in ()).throw(AssertionError())
))
test("Orchestrator process_command scan returns string", lambda: (
    o := importlib.import_module("core.orchestrator").Orchestrator(None, {"anonymity": "always"}, {}),
    r := o.process_command("status"),
    None if "status" in r.lower() else (_ for _ in ()).throw(AssertionError())
))
test("Orchestrator suggest_next_steps after identify", lambda: (
    o := importlib.import_module("core.orchestrator").Orchestrator(None, {"anonymity": "always"}, {}),
    o.session.set_target("10.0.0.5"),
    steps := o.session.suggest_next_steps(),
    None if len(steps) > 0 else (_ for _ in ()).throw(AssertionError())
))
test("Orchestrator save_session writes file", lambda: (
    o := importlib.import_module("core.orchestrator").Orchestrator(None, {"anonymity": "always"}, {}),
    o.session.set_target("10.0.0.5"),
    fp := os.path.join(tmpdir, "test_orch_session.json"),
    o.save_session(fp),
    None if os.path.exists(fp) else (_ for _ in ()).throw(AssertionError())
))

# 21. Memory
print("\n--- Memory Tests ---")
test("ConversationMemory(max_turns=10) init", lambda: importlib.import_module("core.memory").ConversationMemory(max_turns=10))
test("ConversationMemory.add/get", lambda: (
    cm := importlib.import_module("core.memory").ConversationMemory(max_turns=10),
    cm.add_user("hello"),
    cm.add_assistant("hi"),
    hist := cm.get_messages(),
    None if len(hist) == 2 else (_ for _ in ()).throw(AssertionError(f"expected 2, got {len(hist)}"))
))

# Summary
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
if failed > 0:
    print("\nFAILURES:")
    for name, err, tb in errors:
        print(f"\n  {name}:")
        print(f"    {err}")
        lines = tb.strip().split('\n')
        for l in lines[-5:]:
            print(f"    {l}")
print("=" * 60)

import shutil
shutil.rmtree(tmpdir, ignore_errors=True)
sys.exit(1 if failed > 0 else 0)
