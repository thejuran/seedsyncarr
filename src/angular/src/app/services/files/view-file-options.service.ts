import {Inject, Injectable} from "@angular/core";
import {Observable, BehaviorSubject} from "rxjs";

import {LoggerService} from "../utils/logger.service";
import {ViewFileOptions} from "./view-file-options";
import {ViewFile} from "./view-file";
import {LOCAL_STORAGE, StorageService} from "../utils/local-storage.service";
import {StorageKeys} from "../../common/storage-keys";



/**
 * ViewFileOptionsService class provides display option services
 * for view files
 *
 * This class is used to broadcast changes to the display options
 */
@Injectable()
export class ViewFileOptionsService {

    private _options: BehaviorSubject<ViewFileOptions>;

    constructor(private _logger: LoggerService,
                @Inject(LOCAL_STORAGE) private _storage: StorageService) {
        // Load some options from storage
        const sortMethod: ViewFileOptions.SortMethod =
            this._storage.get(StorageKeys.VIEW_OPTION_SORT_METHOD) ||
                ViewFileOptions.SortMethod.STATUS;
        const defaultStatusFilter: ViewFile.Status | null =
            this._storage.get(StorageKeys.VIEW_OPTION_DEFAULT_STATUS_FILTER) || null;

        this._options = new BehaviorSubject(
            new ViewFileOptions({
                sortMethod: sortMethod,
                selectedStatusFilter: defaultStatusFilter,
                nameFilter: "",
            })
        );
    }

    get options(): Observable<ViewFileOptions> {
        return this._options.asObservable();
    }

    public setSortMethod(sortMethod: ViewFileOptions.SortMethod): void {
        const options = this._options.getValue();
        if (options.sortMethod !== sortMethod) {
            const newOptions = new ViewFileOptions(options.set("sortMethod", sortMethod));
            this._options.next(newOptions);
            this._storage.set(StorageKeys.VIEW_OPTION_SORT_METHOD, sortMethod);
            this._logger.debug("ViewOption sortMethod set to: " + newOptions.sortMethod);
        }
    }

    public setSelectedStatusFilter(status: ViewFile.Status | null): void {
        const options = this._options.getValue();
        if (options.selectedStatusFilter !== status) {
            const newOptions = new ViewFileOptions(options.set("selectedStatusFilter", status));
            this._options.next(newOptions);
            this._storage.set(StorageKeys.VIEW_OPTION_DEFAULT_STATUS_FILTER, status);
            this._logger.debug("ViewOption selectedStatusFilter set to: " + newOptions.selectedStatusFilter);
        }
    }

    public setNameFilter(name: string): void {
        const options = this._options.getValue();
        if (options.nameFilter !== name) {
            const newOptions = new ViewFileOptions(options.set("nameFilter", name));
            this._options.next(newOptions);
            this._logger.debug("ViewOption nameFilter set to: " + newOptions.nameFilter);
        }
    }
}
