/*global FolderItem, FootageItem, FileSource, ImportOptions, ImportAsType, Folder, File */
var BootstrapLib = {
    readFile: function (path) {
        var file = new File(path);
        if (!file.exists) {
            throw new Error("Missing file: " + path);
        }
        file.encoding = "UTF-8";
        if (!file.open("r")) {
            throw new Error("Could not read file: " + path);
        }
        var text = file.read();
        file.close();
        return text;
    },

    writeFile: function (path, text) {
        var file = new File(path);
        file.encoding = "UTF-8";
        if (!file.open("w")) {
            throw new Error("Could not write file: " + path);
        }
        file.write(text);
        file.close();
    },

    parseJson: function (text) {
        if (typeof JSON !== "undefined" && JSON.parse) {
            return JSON.parse(text);
        }
        return eval("(" + text + ")");
    },

    quote: function (value) {
        return '"' + String(value)
            .replace(/\\/g, "\\\\")
            .replace(/"/g, '\\"')
            .replace(/\r/g, "\\r")
            .replace(/\n/g, "\\n")
            .replace(/\t/g, "\\t") + '"';
    },

    stringify: function (value) {
        if (value === null || typeof value === "undefined") {
            return "null";
        }
        var type = typeof value;
        if (type === "number" || type === "boolean") {
            return String(value);
        }
        if (type === "string") {
            return BootstrapLib.quote(value);
        }
        var i;
        var parts;
        if (value instanceof Array) {
            parts = [];
            for (i = 0; i < value.length; i++) {
                parts.push(BootstrapLib.stringify(value[i]));
            }
            return "[" + parts.join(",") + "]";
        }
        if (type === "object") {
            parts = [];
            for (i in value) {
                if (value.hasOwnProperty(i)) {
                    parts.push(BootstrapLib.quote(i) + ":" + BootstrapLib.stringify(value[i]));
                }
            }
            return "{" + parts.join(",") + "}";
        }
        return "null";
    },

    normalizePath: function (path) {
        return String(path).replace(/\\/g, "/");
    },

    ensureFolder: function (path) {
        var folder = new Folder(path);
        if (folder.exists) {
            return folder;
        }
        if (folder.parent && !folder.parent.exists) {
            BootstrapLib.ensureFolder(folder.parent.fsName);
        }
        if (!folder.create()) {
            throw new Error("Could not create folder: " + path);
        }
        return folder;
    },

    findFolderByName: function (name) {
        var i;
        for (i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item instanceof FolderItem && item.name === name) {
                return item;
            }
        }
        return null;
    },

    findOrCreateFolder: function (name) {
        var found = BootstrapLib.findFolderByName(name);
        if (found) {
            return found;
        }
        return app.project.items.addFolder(name);
    },

    importFilesIntoFolder: function (paths, folderName) {
        var folder = BootstrapLib.findOrCreateFolder(folderName);
        var imported = [];
        var i;
        for (i = 0; i < paths.length; i++) {
            var file = new File(paths[i]);
            if (!file.exists) {
                throw new Error("Import file missing: " + paths[i]);
            }
            var options = new ImportOptions(file);
            options.importAs = ImportAsType.FOOTAGE;
            var item = app.project.importFile(options);
            item.parentFolder = folder;
            imported.push(item.name);
        }
        return imported;
    },

    isUnderDirectory: function (filePath, directoryPath) {
        var file = BootstrapLib.normalizePath(filePath).toLowerCase();
        var directory = BootstrapLib.normalizePath(directoryPath).toLowerCase();
        if (directory.charAt(directory.length - 1) !== "/") {
            directory += "/";
        }
        return file.indexOf(directory) === 0;
    },

    collectExistingFootage: function (projectRoot, warnings) {
        var footageRoot = BootstrapLib.normalizePath(projectRoot) + "/(Footage)";
        var relinked = [];
        var i;
        for (i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (!(item instanceof FootageItem)) {
                continue;
            }
            if (!item.mainSource || !(item.mainSource instanceof FileSource)) {
                continue;
            }
            var srcFile = item.mainSource.file;
            if (!srcFile) {
                continue;
            }
            if (!srcFile.exists) {
                warnings.push("Skipped missing footage: " + item.name);
                continue;
            }
            var srcPath = srcFile.fsName;
            if (BootstrapLib.isUnderDirectory(srcPath, footageRoot)) {
                continue;
            }

            var parentName = "footage";
            if (item.parentFolder && item.parentFolder !== app.project.rootFolder) {
                parentName = item.parentFolder.name;
            }

            var destDir = BootstrapLib.ensureFolder(footageRoot + "/" + parentName);
            var destFile = new File(destDir.fsName + "/" + srcFile.name);
            if (!destFile.exists) {
                var copied = srcFile.copy(destFile.fsName);
                if (!copied) {
                    warnings.push("Could not copy footage '" + item.name + "' from " + srcPath);
                    continue;
                }
            }
            try {
                item.replace(destFile);
                relinked.push({
                    name: item.name,
                    from: srcPath,
                    to: destFile.fsName
                });
            } catch (replaceError) {
                warnings.push(
                    "Could not relink '" + item.name + "': " +
                    (replaceError && replaceError.message ? replaceError.message : replaceError)
                );
            }
        }
        return relinked;
    },

    writeResult: function (path, result) {
        BootstrapLib.writeFile(path, BootstrapLib.stringify(result));
    }
};
