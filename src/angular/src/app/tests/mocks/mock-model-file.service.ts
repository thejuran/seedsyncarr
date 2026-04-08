import {Subject, Observable} from "rxjs";

import * as Immutable from "immutable";

import {ModelFile} from "../../services/files/model-file";


export class MockModelFileService {

    _files = new Subject<Immutable.Map<string, ModelFile>>();

    get files(): Observable<Immutable.Map<string, ModelFile>> {
        return this._files.asObservable();
    }
}
