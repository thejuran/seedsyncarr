import {fakeAsync, TestBed, tick} from "@angular/core/testing";
import {provideHttpClient} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";

import * as Immutable from "immutable";

import {fileKey} from "../../../../services/files/file-key";
import {ModelFile, ModelFileJson} from "../../../../services/files/model-file";
import {ModelFileService} from "../../../../services/files/model-file.service";
import {ViewFile} from "../../../../services/files/view-file";
import {ViewFileService} from "../../../../services/files/view-file.service";
import {FileSelectionService} from "../../../../services/files/file-selection.service";
import {BulkCommandService, toBulkFile, bulkFileName} from "../../../../services/server/bulk-command.service";
import {LoggerService} from "../../../../services/utils/logger.service";
import {RestService} from "../../../../services/utils/rest.service";
import {StreamServiceRegistry} from "../../../../services/base/stream-service.registry";
import {ConnectedService} from "../../../../services/utils/connected.service";
import {MockStreamServiceRegistry} from "../../../mocks/mock-stream-service.registry";


function modelJson(name: string, pairId: string | null): ModelFileJson {
    return {
        name,
        pair_id: pairId,
        is_dir: false,
        local_size: 0,
        remote_size: 100,
        state: "default",
        downloading_speed: 0,
        eta: 0,
        full_path: "/" + name,
        children: []
    };
}


describe("fileKey", () => {
    it("is the bare name without a pair", () => {
        expect(fileKey(null, "a.mkv")).toBe("a.mkv");
        expect(fileKey(undefined, "a.mkv")).toBe("a.mkv");
        expect(fileKey("", "a.mkv")).toBe("a.mkv");
    });

    it("differs for the same name in two pairs", () => {
        expect(fileKey("tv", "a.mkv")).not.toBe(fileKey("movies", "a.mkv"));
        expect(fileKey("tv", "a.mkv")).not.toBe(fileKey(null, "a.mkv"));
    });

    it("cannot be forged by a name that contains another pair", () => {
        expect(fileKey("tv", "x")).not.toBe(fileKey(null, "tv/x"));
        expect(fileKey("tv", "x")).not.toBe(fileKey(null, "tv\u0000x".slice(0, 2) + "x"));
    });
});


describe("ModelFile pair_id", () => {
    it("is read from the JSON", () => {
        expect(ModelFile.fromJson(modelJson("a", "tv")).pair_id).toBe("tv");
    });

    it("is null when the backend sends none", () => {
        const json = modelJson("a", null);
        delete json.pair_id;
        expect(ModelFile.fromJson(json).pair_id).toBeNull();
    });
});


describe("ModelFileService with path pairs", () => {
    let service: ModelFileService;
    let httpMock: HttpTestingController;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), LoggerService, RestService, ModelFileService]
        });
        httpMock = TestBed.inject(HttpTestingController);
        service = TestBed.inject(ModelFileService);
    });

    function latest(): Immutable.Map<string, ModelFile> {
        let model = Immutable.Map<string, ModelFile>();
        service.files.subscribe(m => model = m).unsubscribe();
        return model;
    }

    it("keeps one entry per pair for the same file name", fakeAsync(() => {
        service.notifyEvent("model-init", JSON.stringify([modelJson("same", "tv"), modelJson("same", "movies")]));
        tick();
        expect(latest().size).toBe(2);
        expect(latest().get(fileKey("tv", "same"))!.pair_id).toBe("tv");
        expect(latest().get(fileKey("movies", "same"))!.pair_id).toBe("movies");
    }));

    it("adds, updates and removes only the file of its pair", fakeAsync(() => {
        service.notifyEvent("model-init", JSON.stringify([modelJson("same", "tv"), modelJson("same", "movies")]));
        const updated = {...modelJson("same", "tv"), remote_size: 555};
        service.notifyEvent("model-updated", JSON.stringify({old_file: modelJson("same", "tv"), new_file: updated}));
        tick();
        expect(latest().get(fileKey("tv", "same"))!.remote_size).toBe(555);
        expect(latest().get(fileKey("movies", "same"))!.remote_size).toBe(100);

        service.notifyEvent("model-removed", JSON.stringify({old_file: modelJson("same", "tv"), new_file: null}));
        tick();
        expect(latest().size).toBe(1);
        expect(latest().has(fileKey("movies", "same"))).toBeTrue();

        service.notifyEvent("model-added", JSON.stringify({old_file: null, new_file: modelJson("same", "tv")}));
        tick();
        expect(latest().size).toBe(2);
    }));

    it("sends the pair id with every command", fakeAsync(() => {
        service.notifyConnected();
        const file = ModelFile.fromJson(modelJson("a b", "tv"));

        service.queue(file).subscribe();
        httpMock.expectOne(r => r.url === "/server/command/queue/a%2520b?pair_id=tv" && r.method === "POST").flush("");
        service.stop(file).subscribe();
        httpMock.expectOne(r => r.url === "/server/command/stop/a%2520b?pair_id=tv" && r.method === "POST").flush("");
        service.extract(file).subscribe();
        httpMock.expectOne(r => r.url === "/server/command/extract/a%2520b?pair_id=tv" && r.method === "POST").flush("");
        service.deleteLocal(file).subscribe();
        httpMock.expectOne(r => r.url === "/server/command/delete_local/a%2520b?pair_id=tv" && r.method === "DELETE").flush("");
        service.deleteRemote(file).subscribe();
        httpMock.expectOne(r => r.url === "/server/command/delete_remote/a%2520b?pair_id=tv" && r.method === "DELETE").flush("");
        tick();
        httpMock.verify();
    }));

    it("leaves the URL unchanged without a pair", fakeAsync(() => {
        service.notifyConnected();
        service.queue(ModelFile.fromJson(modelJson("a", null))).subscribe();
        httpMock.expectOne("/server/command/queue/a").flush("");
        tick();
        httpMock.verify();
    }));
});


describe("ViewFileService with path pairs", () => {
    let viewService: ViewFileService;
    let mockModel: { _files: { next: (m: Immutable.Map<string, ModelFile>) => void } };

    function modelMap(files: ModelFile[]): Immutable.Map<string, ModelFile> {
        return Immutable.Map<string, ModelFile>(files.map(f => [fileKey(f.pair_id, f.name), f]));
    }

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [
                ViewFileService,
                LoggerService,
                ConnectedService,
                FileSelectionService,
                {provide: StreamServiceRegistry, useClass: MockStreamServiceRegistry}
            ]
        });
        viewService = TestBed.inject(ViewFileService);
        mockModel = (TestBed.inject(StreamServiceRegistry) as unknown as MockStreamServiceRegistry).modelFileService as never;
    });

    function latest(): Immutable.List<ViewFile> {
        let list = Immutable.List<ViewFile>();
        viewService.files.subscribe(l => list = l).unsubscribe();
        return list;
    }

    it("shows the same file name in two pairs as two rows", fakeAsync(() => {
        mockModel._files.next(modelMap([
            ModelFile.fromJson(modelJson("same", "tv")), ModelFile.fromJson(modelJson("same", "movies"))
        ]));
        tick();
        expect(latest().size).toBe(2);
        expect(latest().map(f => f.pairId).toArray().sort()).toEqual(["movies", "tv"]);
        expect(new Set(latest().map(f => f.key).toArray()).size).toBe(2);
    }));

    it("updates and removes only the row of its pair", fakeAsync(() => {
        const tv = ModelFile.fromJson(modelJson("same", "tv"));
        const movies = ModelFile.fromJson(modelJson("same", "movies"));
        mockModel._files.next(modelMap([tv, movies]));
        tick();

        mockModel._files.next(modelMap([tv.set("remote_size", 999) as ModelFile, movies]));
        tick();
        expect(latest().find(f => f.pairId === "tv")!.remoteSize).toBe(999);
        expect(latest().find(f => f.pairId === "movies")!.remoteSize).toBe(100);

        mockModel._files.next(modelMap([movies]));
        tick();
        expect(latest().size).toBe(1);
        expect(latest().get(0)!.pairId).toBe("movies");
    }));

    it("marks only the clicked file of a shared name as selected", fakeAsync(() => {
        mockModel._files.next(modelMap([
            ModelFile.fromJson(modelJson("same", "tv")), ModelFile.fromJson(modelJson("same", "movies"))
        ]));
        tick();
        viewService.setSelected(latest().find(f => f.pairId === "movies")!);
        expect(latest().find(f => f.pairId === "movies")!.isSelected).toBeTrue();
        expect(latest().find(f => f.pairId === "tv")!.isSelected).toBeFalsy();
    }));
});


describe("FileSelectionService with path pairs", () => {
    it("selects every visible file by key, so shared names stay separate", () => {
        const selection = TestBed.inject(FileSelectionService);
        const tv = new ViewFile({name: "same", pairId: "tv"});
        const movies = new ViewFile({name: "same", pairId: "movies"});
        selection.selectAllVisible([tv, movies]);
        expect(selection.getSelectedCount()).toBe(2);
        selection.deselect(tv.key);
        expect(selection.isSelected(tv.key)).toBeFalse();
        expect(selection.isSelected(movies.key)).toBeTrue();
    });
});


describe("BulkCommandService with path pairs", () => {
    let service: BulkCommandService;
    let httpMock: HttpTestingController;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), BulkCommandService, LoggerService]
        });
        service = TestBed.inject(BulkCommandService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    it("sends names for files without a pair and name and pair otherwise", fakeAsync(() => {
        service.executeBulkAction("queue", ["plain", {name: "same", pairId: "tv"}, {name: "same", pairId: "movies"}])
            .subscribe();
        const req = httpMock.expectOne("/server/command/bulk");
        expect(req.request.body).toEqual({
            action: "queue",
            files: ["plain", {name: "same", pair_id: "tv"}, {name: "same", pair_id: "movies"}]
        });
        req.flush({results: [], summary: {total: 0, succeeded: 0, failed: 0}});
        tick();
        httpMock.verify();
    }));

    it("builds bulk files only with a pair", () => {
        expect(toBulkFile("a", null)).toBe("a");
        expect(toBulkFile("a", "tv")).toEqual({name: "a", pairId: "tv"});
        expect(bulkFileName("a")).toBe("a");
        expect(bulkFileName({name: "a", pairId: "tv"})).toBe("a");
    });
});
