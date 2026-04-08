import {fakeAsync, TestBed, tick} from "@angular/core/testing";

import {ViewFileOptionsService} from "../../../../services/files/view-file-options.service";
import {ViewFileOptions} from "../../../../services/files/view-file-options";
import {ViewFile} from "../../../../services/files/view-file";
import {LoggerService} from "../../../../services/utils/logger.service";
import {MockStorageService} from "../../../mocks/mock-storage.service";
import {LOCAL_STORAGE, StorageService} from "../../../../services/utils/local-storage.service";
import {StorageKeys} from "../../../../common/storage-keys";


function createViewOptionsService(): ViewFileOptionsService {
    return new ViewFileOptionsService(
        TestBed.inject(LoggerService),
        TestBed.inject(LOCAL_STORAGE)
    );
}


describe("Testing view file options service", () => {
    let viewOptionsService: ViewFileOptionsService;
    let storageService: StorageService;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [
                ViewFileOptionsService,
                LoggerService,
                {provide: LOCAL_STORAGE, useClass: MockStorageService},
            ]
        });

        viewOptionsService = TestBed.inject(ViewFileOptionsService);

        storageService = TestBed.inject(LOCAL_STORAGE);
    });

    it("should create an instance", () => {
        expect(viewOptionsService).toBeDefined();
    });

    it("should forward default options", fakeAsync(() => {
        let count = 0;

        viewOptionsService.options.subscribe({
            next: options => {
                expect(options.sortMethod).toBe(ViewFileOptions.SortMethod.STATUS);
                expect(options.selectedStatusFilter).toBeNull();
                expect(options.nameFilter).toBe("");
                count++;
            }
        });

        tick();
        expect(count).toBe(1);
    }));

    it("should forward updates to sortMethod", fakeAsync(() => {
        let count = 0;
        let sortMethod: ViewFileOptions.SortMethod | null = null;
        viewOptionsService.options.subscribe({
            next: options => {
                sortMethod = options.sortMethod;
                count++;
            }
        });
        tick();
        expect(count).toBe(1);

        viewOptionsService.setSortMethod(ViewFileOptions.SortMethod.NAME_ASC);
        tick();
        expect(sortMethod!).toBe(ViewFileOptions.SortMethod.NAME_ASC);
        expect(count).toBe(2);

        viewOptionsService.setSortMethod(ViewFileOptions.SortMethod.NAME_DESC);
        tick();
        expect(sortMethod!).toBe(ViewFileOptions.SortMethod.NAME_DESC);
        expect(count).toBe(3);

        // Setting same value shouldn't trigger an update
        viewOptionsService.setSortMethod(ViewFileOptions.SortMethod.NAME_DESC);
        tick();
        expect(sortMethod!).toBe(ViewFileOptions.SortMethod.NAME_DESC);
        expect(count).toBe(3);
    }));

    it("should load sortMethod from storage", fakeAsync(() => {
        spyOn(storageService, "get").and.callFake(<T = unknown>(key: string): T | null => {
            if (key === StorageKeys.VIEW_OPTION_SORT_METHOD) {
                return ViewFileOptions.SortMethod.NAME_ASC as T;
            }
            return null;
        });
        // Recreate the service
        viewOptionsService = createViewOptionsService();

        let count = 0;
        let sortMethod: ViewFileOptions.SortMethod | null = null;
        viewOptionsService.options.subscribe({
            next: options => {
                sortMethod = options.sortMethod;
                count++;
            }
        });
        tick();
        expect(count).toBe(1);
        expect(sortMethod!).toBe(ViewFileOptions.SortMethod.NAME_ASC);
    }));

    it("should save sortMethod to storage", fakeAsync(() => {
        spyOn(storageService, "set");
        viewOptionsService.setSortMethod(ViewFileOptions.SortMethod.NAME_ASC);
        expect(storageService.set).toHaveBeenCalledWith(
            StorageKeys.VIEW_OPTION_SORT_METHOD,
            ViewFileOptions.SortMethod.NAME_ASC
        );
        viewOptionsService.setSortMethod(ViewFileOptions.SortMethod.NAME_DESC);
        expect(storageService.set).toHaveBeenCalledWith(
            StorageKeys.VIEW_OPTION_SORT_METHOD,
            ViewFileOptions.SortMethod.NAME_DESC
        );
    }));

    it("should forward updates to selectedStatusFilter", fakeAsync(() => {
        let count = 0;
        let selectedStatusFilter: ViewFile.Status | null = null;
        viewOptionsService.options.subscribe({
            next: options => {
                selectedStatusFilter = options.selectedStatusFilter;
                count++;
            }
        });
        tick();
        expect(count).toBe(1);

        viewOptionsService.setSelectedStatusFilter(ViewFile.Status.EXTRACTED);
        tick();
        expect(selectedStatusFilter!).toBe(ViewFile.Status.EXTRACTED);
        expect(count).toBe(2);

        viewOptionsService.setSelectedStatusFilter(ViewFile.Status.QUEUED);
        tick();
        expect(selectedStatusFilter!).toBe(ViewFile.Status.QUEUED);
        expect(count).toBe(3);

        // Setting same value shouldn't trigger an update
        viewOptionsService.setSelectedStatusFilter(ViewFile.Status.QUEUED);
        tick();
        expect(selectedStatusFilter!).toBe(ViewFile.Status.QUEUED);
        expect(count).toBe(3);

        // Null should be allowed
        viewOptionsService.setSelectedStatusFilter(null as unknown as ViewFile.Status);
        tick();
        expect(selectedStatusFilter).toBeNull();
        expect(count).toBe(4);
    }));

    it("should forward updates to nameFilter", fakeAsync(() => {
        let count = 0;
        let nameFilter: string | null = null;
        viewOptionsService.options.subscribe({
            next: options => {
                nameFilter = options.nameFilter;
                count++;
            }
        });
        tick();
        expect(count).toBe(1);

        viewOptionsService.setNameFilter("tofu");
        tick();
        expect(nameFilter!).toBe("tofu");
        expect(count).toBe(2);

        viewOptionsService.setNameFilter("flower");
        tick();
        expect(nameFilter!).toBe("flower");
        expect(count).toBe(3);

        // Setting same value shouldn't trigger an update
        viewOptionsService.setNameFilter("flower");
        tick();
        expect(nameFilter!).toBe("flower");
        expect(count).toBe(3);

        // Null should be allowed
        viewOptionsService.setNameFilter(null as unknown as string);
        tick();
        expect(nameFilter).toBeNull();
        expect(count).toBe(4);
    }));
});
