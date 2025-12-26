import json

# Load task def
with open("task-def-reg.json") as f:
    td = json.load(f)

# Update CORS env var
for env in td["containerDefinitions"][0]["environment"]:
    if env["name"] == "BACKEND_CORS_ORIGINS":
        env["value"] = (
            "https://cricksy-ai.web.app,https://app.cricksy-ai.com,https://api.cricksy-ai.com,http://localhost:5173,http://localhost:3000,http://localhost:5174,http://localhost:4173,https://cricksy-ai.com,https://www.cricksy-ai.com,https://dev.cricksy-ai.com"
        )
        print("Updated CORS to include all required domains")

# Save
with open("task-def-reg-updated.json", "w") as f:
    json.dump(td, f, indent=2)

print("Saved updated task definition")
