{
  "gitSyncId": "69c8f9130b20713d33eec660_tmo_js_body_001",
  "id": "TeamMailout_MailoutJS_body",
  "unpublishedCollection": {
    "name": "MailoutJS",
    "pageId": "TeamMailout",
    "pluginId": "js-plugin",
    "pluginType": "JS",
    "body": "export default {\n  statusMessage: \"Ready to generate or send the current team mailout bundle\",\n  isRunning: false,\n\n  formatResult(result, fallback) {\n    if (typeof result === 'string' && result.trim()) return result.trim();\n    if (result && typeof result === 'object') {\n      if (typeof result.message === 'string' && result.message.trim()) return result.message.trim();\n      if (typeof result.error === 'string' && result.error.trim()) return `Error: ${result.error.trim()}`;\n      const serialized = JSON.stringify(result, null, 2);\n      if (serialized && serialized !== '{}') return serialized;\n    }\n    return fallback;\n  },\n\n  markReady() {\n    this.statusMessage = `Ready for ${ToggleTestMode.isSelected ? 'test' : 'production'} mailout in ${SelectScope.selectedOptionValue || 'all-in-section'} mode`;\n  },\n\n  async runGenerateAndSend() {\n    this.isRunning = true;\n    this.statusMessage = `Preparing ${ToggleTestMode.isSelected ? 'test' : 'production'} captain mailout...`;\n\n    try {\n      const result = await GenerateContactSheets.run();\n      this.statusMessage = this.formatResult(result, 'Captain mailout sent successfully.');\n    } catch (error) {\n      this.statusMessage = `Error: ${error?.message || 'Unknown error occurred'}`;\n      throw error;\n    } finally {\n      this.isRunning = false;\n    }\n  },\n\n  async runGenerateOnly() {\n    this.isRunning = true;\n    this.statusMessage = 'Refreshing the current mailout bundle...';\n\n    try {\n      const result = await GenerateOnly.run();\n      this.statusMessage = this.formatResult(result, 'Captain mailout bundle refreshed.');\n    } catch (error) {\n      this.statusMessage = `Error: ${error?.message || 'Unknown error occurred'}`;\n      throw error;\n    } finally {\n      this.isRunning = false;\n    }\n  }\n}"
  }
}
