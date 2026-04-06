{
  "gitSyncId": "69c8f9130b20713d33eec660_tmo_js_body_001",
  "id": "TeamMailout_MailoutJS_body",
  "unpublishedCollection": {
    "name": "MailoutJS",
    "pageId": "TeamMailout",
    "pluginId": "js-plugin",
    "pluginType": "JS",
    "body": "export default {\n  statusMessage: \"Ready to generate and send team contact sheets\",\n  isRunning: false,\n\n  async runGenerateAndSend() {\n    this.isRunning = true;\n    this.statusMessage = \"Starting mailout process...\";\n\n    try {\n      const category = SelectCategory.selectedOptionValue;\n      const scope = SelectScope.selectedOptionValue;\n      const testMode = ToggleTestMode.isSelected;\n\n      this.statusMessage = \"Step 1: Generating team contact sheets...\";\n      await GenerateContactSheets.run();\n\n      this.statusMessage = \"Step 2: Syncing mailout data to n8n...\";\n      await SyncMailoutData.run();\n\n      this.statusMessage = \"Step 3: Sending captain emails\" + (testMode ? \" (test mode)\" : \"\") + \"...\";\n      await TriggerMailout.run();\n\n      this.statusMessage = \"Mailout complete! \" + (testMode ? \"(Test mode - emails sent to test recipient)\" : \"(Production mode - emails sent to captains)\");\n    } catch (error) {\n      this.statusMessage = \"Error: \" + (error.message || \"Unknown error occurred\");\n    } finally {\n      this.isRunning = false;\n    }\n  },\n\n  async runGenerateOnly() {\n    this.isRunning = true;\n    this.statusMessage = \"Generating team contact sheets...\";\n\n    try {\n      await GenerateOnly.run();\n      this.statusMessage = \"Contact sheets generated successfully. Check Teams/generated/ folder.\";\n    } catch (error) {\n      this.statusMessage = \"Error: \" + (error.message || \"Unknown error occurred\");\n    } finally {\n      this.isRunning = false;\n    }\n  }\n}"
  }
}
