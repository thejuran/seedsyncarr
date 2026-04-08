import {Injectable} from "@angular/core";
import {Observable, BehaviorSubject} from "rxjs";


/**
 * DomService facilitates inter-component communication related
 * to DOM updates
 */
@Injectable()
export class DomService {
    private _headerHeight: BehaviorSubject<number> = new BehaviorSubject(0);

    get headerHeight(): Observable<number>{
        return this._headerHeight.asObservable();
    }

    public setHeaderHeight(height: number): void {
        if(height !== this._headerHeight.getValue()) {
            this._headerHeight.next(height);
        }
    }

}
