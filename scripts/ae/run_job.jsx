/*global BootstrapLib, BOOTSTRAP_JOB_PATH, CloseOptions, File */
(function () {
    var libFile = new File($.fileName);
    $.evalFile(new File(libFile.parent.fsName + "/lib.jsx"));

    function defaultResultPath(jobFilePath) {
        var jobFile = new File(jobFilePath);
        return BootstrapLib.normalizePath(jobFile.parent.fsName) + "/result.json";
    }

    function closeOpenProject() {
        if (app.project) {
            app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        }
    }

    function openProject(path, label) {
        var file = new File(path);
        if (!file.exists) {
            throw new Error(label + " missing: " + path);
        }
        var project = app.open(file);
        if (!project) {
            throw new Error("Failed to open " + label + ": " + path);
        }
        return project;
    }

    var result = {
        ok: false,
        imported_main: [],
        imported_preprocess: [],
        relinked: [],
        warnings: [],
        errors: []
    };
    var resultPath = null;
    var job = null;

    try {
        if (typeof BOOTSTRAP_JOB_PATH === "undefined" || !BOOTSTRAP_JOB_PATH) {
            throw new Error("BOOTSTRAP_JOB_PATH is not set");
        }
        resultPath = defaultResultPath(BOOTSTRAP_JOB_PATH);
        job = BootstrapLib.parseJson(BootstrapLib.readFile(BOOTSTRAP_JOB_PATH));
        if (job.result_path) {
            resultPath = job.result_path;
        }

        app.beginSuppressDialogs();
        closeOpenProject();

        openProject(job.main_template, "Main template");
        app.project.save(new File(job.main_save_as));
        result.imported_main = BootstrapLib.importFilesIntoFolder(
            job.import_files || [],
            job.main_import_folder
        );
        if (job.collect_existing) {
            result.relinked = BootstrapLib.collectExistingFootage(
                job.project_root,
                result.warnings
            );
        }
        app.project.save();
        app.project.close(CloseOptions.SAVE_CHANGES);

        openProject(job.preprocess_template, "Pre-process template");
        app.project.save(new File(job.preprocess_save_as));
        result.imported_preprocess = BootstrapLib.importFilesIntoFolder(
            job.import_files || [],
            job.preprocess_import_folder
        );
        app.project.save();
        app.project.close(CloseOptions.SAVE_CHANGES);

        result.ok = true;
        app.exitCode = 0;
        BootstrapLib.writeResult(resultPath, result);
    } catch (error) {
        result.ok = false;
        result.errors.push(error && error.message ? String(error.message) : String(error));
        app.exitCode = 1;
        if (resultPath) {
            try {
                BootstrapLib.writeResult(resultPath, result);
            } catch (writeError) {
                // The Python side will time out if this write also fails.
            }
        }
    } finally {
        try {
            app.endSuppressDialogs(false);
        } catch (ignore) {
        }
    }
})();
