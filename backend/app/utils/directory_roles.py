import re
from typing import Any, Dict, List

def detect_directory_roles(dirs: List[str]) -> List[Dict[str, Any]]:
    """Determine architectural roles of directories based on naming patterns."""
    role_patterns = {
        "core": [r"\bcore\b", r"\bkernel\b"],
        "library/package": [r"\blibs\b", r"\blib\b", r"\bpackages\b", r"\bpkg\b"],
        "provider": [r"\bproviders\b", r"\bprovider\b"],
        "partner/integration": [r"\bintegration\b", r"\bintegrations\b", r"\bpartner\b", r"\bpartners\b"],
        "adapter": [r"\badapters\b", r"\badapter\b"],
        "model": [r"\bmodels\b", r"\bmodel\b", r"\bschema\b", r"\bschemas\b"],
        "agent": [r"\bagents\b", r"\bagent\b"],
        "middleware": [r"\bmiddleware\b", r"\bmiddlewares\b"],
        "service": [r"\bservices\b", r"\bservice\b"],
        "API": [r"\bapi\b", r"\bapis\b", r"\bendpoints\b", r"\bcontrollers\b"],
        "CLI": [r"\bcli\b", r"\bcmd\b", r"\bcommand\b", r"\bcommands\b"],
        "database/storage": [r"\bdb\b", r"\bdatabase\b", r"\bstorage\b", r"\bsql\b", r"\bmigrations\b", r"\bmigration\b"],
        "retrieval": [r"\bretrieval\b", r"\bretrieve\b", r"\bvectorstore\b", r"\bindex\b"],
        "tooling": [r"\btooling\b", r"\btools\b", r"\btool\b"],
        "utility": [r"\butilities\b", r"\butility\b", r"\butils\b", r"\butil\b", r"\bhelpers\b", r"\bhelper\b"],
        "configuration": [r"\bconfig\b", r"\bconfigs\b", r"\bsettings\b"],
        "documentation": [r"\bdocs\b", r"\bdoc\b", r"\bdocumentation\b"],
        "tests": [r"\btest\b", r"\btests\b", r"\btesting\b", r"\bspec\b", r"\bspecs\b"],
        "examples": [r"\bexamples\b", r"\bexample\b", r"\bsamples\b", r"\bsample\b"],
        "scripts": [r"\bscripts\b", r"\bscript\b", r"\bbin\b"]
    }
    
    inferred = []
    for d in dirs:
        parts = d.lower().split("/")
        roles = []
        evidence = []
        for role, patterns in role_patterns.items():
            for p in patterns:
                matched = False
                for part in parts:
                    if re.search(p, part):
                        roles.append(role)
                        evidence.append(f"directory token: {part}")
                        matched = True
                        break
                if matched:
                    break
        if roles:
            inferred.append({
                "path": d,
                "roles": roles,
                "evidence": list(sorted(list(set(evidence))))
            })
    return inferred
