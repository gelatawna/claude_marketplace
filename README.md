# Claude DI Marketplace

This repository serves as the plugin marketplace for distributing BDAP-DI plugins to Claude Code users within the BDAP community.

Marketplace Name: **BDAP_DI_marketplace**

Plugins:
* **bdap-di** - The main plugin of the BDAP-DI ecosystem, providing various skills and agents e.g. for data integration tasks.

Claude References: 
* https://code.claude.com/docs/en/discover-plugins, 
* https://code.claude.com/docs/en/plugin-marketplaces

## Installation
Find a detailed installation guide in the [Claude Code documentation](https://code.claude.com/docs/en/discover-plugins#installing-plugins-from-marketplaces).

### Installation Steps
As an overview, the installation process includes the following steps:

1. Set your GITLAB_TOKEN to get access to the private repository if you want to install the plugin via the marketplace. The token must have at least read access to the repository.

2. The plugin is distributed via the marketplace. To install it via Claude Code CLI use the:
* /plugin command, 
* Select "Marketplaces"
* Chose "+ Add Marketplace".
* Set `git@gitlab.com:tchibo-com/bi/sap-di/claude-di-marketplace.git` or a local path to this repository as the marketplace source.
* Set the scope where the plugin should be enabled e.g. user scope, project scope or local scope.
* Restart Claude Code CLI to load the plugin.

Or run the first steps at once like:

* Add the **BDAP_DI_marketplace**
  * `/plugin marketplace add git@gitlab.com:tchibo-com/bi/sap-di/claude-di-marketplace.git`  

* Install plugins from the marketplace like **bdap-di** plugin
  * `/plugin install bdap-di@BDAP_DI_marketplace`

To register the marketplace manually, follow these steps:
1. Ensure the marketplace is registered in your`~/.claude/plugins/known_marketplaces.json`:
```json
{
  "BDAP_DI_marketplace": "git@gitlab.com:tchibo-com/bi/sap-di/claude-di-marketplace.git",
      "source": {
      "source": "git",
      "url": "git@gitlab.com:tchibo-com/bi/sap-di/claude-di-marketplace.git"
    }
}
```

2. Enable the plugin e.g. in the user-scope `~/.claude/settings.json`:
```json
{
  "permissions": {
    "bdap-plugin@bdap-di": true
  }
}
```

Always restart Claude Code CLI to load the plugin and changes.
