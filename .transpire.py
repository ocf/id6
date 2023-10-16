from pathlib import Path

from transpire.resources import Deployment, Ingress, Service, ConfigMap, Secret
from transpire.types import Image
from transpire.utils import get_image_tag

name = "id6"

config = """
# Logging and admin configuration.
# Channel ID to send logs & manage the bot.
admin_channel = 739590063700181056
verify_channel = 763850790049284106

# Information about verification.
# Base web URL (proxy it through keycloak gatekeeper).
base_url = "https://discord.ocf.berkeley.edu"
# Guild ID to act in (currently an unused config option- just make the bot private).
guild_id = 735620315111096391
# Role ID to assign to people who verify themselves.
role_id = 737454417904664687
# Message to listen to reactions on.
msg_id = 764650095161376798
"""

def objects():
    yield {
        "apiVersion": "acid.zalan.do/v1",
        "kind": "postgresql",
        "metadata": {"name": "ocf-id6"},
        "spec": {
            "teamId": "ocf",
            "volume": {
                "size": "8Gi",
                "storageClass": "rbd-nvme",
            },
            "numberOfInstances": 1,
            "users": {"id6": ["superuser", "createdb"]},
            "databases": {"id6": "id6"},
            "postgresql": {"version": "15"},
        },
    }

    yield Secret(
        name="id6",
        string_data={
            "discord-token": "",
            "config_path": "",
            "postgres": "",
            "keycloak": "",
            "encryption_key": "",
        },
    ).build()

    cm = ConfigMap("id6", data={"config.toml": config})
    yield cm.build()

    dep = Deployment(
        name="id6",
        image=get_image_tag("id6"),
        ports=[8080],
    )
    dep.obj.spec.template.spec.volumes = [
        {
            "name": "id6",
            "configMap": {"name": cm.obj.metadata.name},
        },
    ]
    dep.obj.spec.template.spec.containers[0].volume_mounts = [
        {
            "name": "id6",
            "mountPath": "/config",
        }
    ]

    dep.obj.spec.template.spec.containers[0].env = [
        {
            "name": "_DB_USER",
            "valueFrom": {
                "secretKeyRef": {
                    "name": "id6.ocf-id6.credentials.postgresql.acid.zalan.do",
                    "key": "username",
                }
            },
        },
        {
            "name": "_DB_PASS",
            "valueFrom": {
                "secretKeyRef": {
                    "name": "id6.ocf-id6.credentials.postgresql.acid.zalan.do",
                    "key": "password",
                }
            },
        },
        {
            "name": "DISCORD_TOKEN",
            "valueFrom": {
                "secretKeyRef": {
                    "name": "id6",
                    "key": "discord-token",
                }
            },
        },
        {
            "name": "CONFIG_FILE_PATH",
            "valueFrom": {
                "secretKeyRef": {
                    "name": "id6",
                    "key": "config_path",
                }
            },
        },
        {
            "name": "POSTGRES_CONN",
            "value": "postgres://$(_DB_USER):$(_DB_PASS)@ocf-notes:5432/notes?ssl=no-verify"
        },
     ]
    dep_proxy = Deployment(
        name="id6-proxy",
        image="quay.io/keycloak/keycloak-gatekeeper:6.0.1",
        ports=[8000],
        args=[
            "--client-id=id6", 
            "--client-secret=$(KEYCLOAK_SECRET)",
            "--encryption-key=$(ENCRYPTION_KEY)",
            "--redirection-url=https://discord.ocf.berkeley.edu/",
            "--discovery-url=https://idm.ocf.berkeley.edu/realms/ocf",
            "--enable-default-deny=true",
            "--enable-session-cookies",
            "--listen=:8000",
            "--upstream-url=http://id6",
            "--resources=uri=/*",
            "--headers=Host=discord.ocf.berkeley.edu",]
    )
    
    dep_proxy.obj.spec.template.spec.containers[0].env = [
        {
            "name": "KEYCLOAK_SECRET",
            "valueFrom": {
                "secretKeyRef": {
                    "name": "id6",
                    "key": "keycloak",
                }
            },
        },
        {
            "name": "ENCRYPTION_KEY",
            "valueFrom": {
                "secretKeyRef": {
                    "name": "id6",
                    "key": "encryption_key",
                }
            },
        },
     ]

    svc = Service(
        name="id6",
        selector=dep.get_selector(),
        port_on_pod=8080,
        port_on_svc=80,
    )

    svc_proxy = Service(
        name="id6-proxy",
        selector=dep_worker.get_selector(),
        port_on_pod=8000,
        port_on_svc=80,
    )

    ing_proxy = Ingress.from_svc(
        svc=svc_worker,
        host="discord.ocf.berkeley.edu",
        path_prefix="/",
    )

    yield dep.build()
    yield svc.build()

    yield dep_proxy.build()
    yield svc_proxy.build()
    yield ing_proxy.build()


def images():
    yield Image(name="id6", path=Path("/"))