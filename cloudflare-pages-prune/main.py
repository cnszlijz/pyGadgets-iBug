#!/usr/bin/python3

import datetime
import os
import sys

import cloudflare
from pydantic import BaseModel


class Config(BaseModel):
    account_id: str
    api_token: str


def main():
    os.chdir(os.path.dirname(__file__))
    with open("config.json", "r") as f:
        config = Config.model_validate_json(f.read())

    account_id = config.account_id
    client = cloudflare.Cloudflare(api_token=config.api_token)
    expiry = datetime.timedelta(days=30)

    for project in client.pages.projects.list(account_id=account_id):
        project_name = project.name
        deployments = list(client.pages.projects.deployments.list(project_name, account_id=account_id))
        print(f"Working on {project_name}, {len(deployments)} deployments")

        canonical_id = project.canonical_deployment.id
        for deployment in deployments:
            if deployment.id == canonical_id:
                continue
            if deployment.aliases:
                # has an active deployment, skip
                continue
            short_id = deployment.short_id or deployment.id
            if deployment.is_skipped:
                print(f"  Delete {short_id}: is skipped")
                try:
                    client.pages.projects.deployments.delete(
                        deployment.id,
                        account_id=account_id,
                        project_name=project_name,
                    )
                except cloudflare.APIError as e:
                    print(f"  Failed to delete {short_id}: {e}", file=sys.stderr)
                continue

            created_on = deployment.created_on
            now = datetime.datetime.now()
            delta = now - created_on
            if delta >= expiry:
                print(f"  Delete {short_id}: is {delta.days} days old ({created_on.isoformat()})")
                try:
                    client.pages.projects.deployments.delete(
                        deployment.id,
                        account_id=account_id,
                        project_name=project_name,
                    )
                except cloudflare.APIError as e:
                    print(f"  Failed to delete {short_id}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
