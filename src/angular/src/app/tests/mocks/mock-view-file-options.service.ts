import {Subject, Observable} from "rxjs";

import {ViewFileOptions} from "../../services/files/view-file-options";


export class MockViewFileOptionsService {

    _options = new Subject<ViewFileOptions>();

    get options(): Observable<ViewFileOptions> {
        return this._options.asObservable();
    }
}
