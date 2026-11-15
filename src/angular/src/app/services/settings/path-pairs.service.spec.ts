import {TestBed} from "@angular/core/testing";
import {of} from "rxjs";

import {PathPairsService} from "./path-pairs.service";
import {RestService, WebReaction} from "../utils/rest.service";
import {LoggerService} from "../utils/logger.service";
import {PathPair} from "./path-pair";

describe("PathPairsService", () => {
    let service: PathPairsService;
    let rest: jasmine.SpyObj<RestService>;

    const pair: PathPair = {
        id: "default", name: "Default", remote_path: "/r", local_path: "/l", enabled: true, auto_queue: true
    };
    const listReaction = (pairs: PathPair[]): WebReaction =>
        new WebReaction(true, JSON.stringify({path_pairs: pairs}), null);

    beforeEach(() => {
        rest = jasmine.createSpyObj("RestService", ["sendRequest", "post"]);
        rest.sendRequest.and.returnValue(of(listReaction([pair])));
        TestBed.configureTestingModule({
            providers: [
                PathPairsService,
                {provide: RestService, useValue: rest},
                {provide: LoggerService, useValue: jasmine.createSpyObj("LoggerService", ["debug", "error"])},
            ]
        });
        service = TestBed.inject(PathPairsService);
    });

    function latest(): PathPair[] {
        let value: PathPair[] = [];
        service.pairs.subscribe(p => value = p).unsubscribe();
        return value;
    }

    it("starts empty", () => {
        expect(latest()).toEqual([]);
    });

    it("refresh loads the pairs", () => {
        service.refresh();
        expect(rest.sendRequest).toHaveBeenCalledWith("/server/pathpairs");
        expect(latest()).toEqual([pair]);
    });

    it("refresh keeps the pairs when the request fails", () => {
        service.refresh();
        rest.sendRequest.and.returnValue(of(new WebReaction(false, null, "down")));
        service.refresh();
        expect(latest()).toEqual([pair]);
    });

    it("refresh ignores an unparsable response", () => {
        rest.sendRequest.and.returnValue(of(new WebReaction(true, "not json", null)));
        service.refresh();
        expect(latest()).toEqual([]);
    });

    it("create posts the input and refreshes on success", () => {
        rest.post.and.returnValue(of(new WebReaction(true, "{}", null)));
        const input = {name: "tv", remote_path: "/r/tv", local_path: "/l/tv"};
        service.create(input).subscribe();
        expect(rest.post).toHaveBeenCalledWith("/server/pathpairs/create", input);
        expect(rest.sendRequest).toHaveBeenCalledTimes(1);
    });

    it("does not refresh when a change fails", () => {
        rest.post.and.returnValue(of(new WebReaction(false, null, "conflict")));
        service.create({name: "tv", remote_path: "/r", local_path: "/l"}).subscribe();
        service.update("x", {enabled: false}).subscribe();
        service.remove("x").subscribe();
        expect(rest.sendRequest).not.toHaveBeenCalled();
    });

    it("update posts the changes to the encoded id", () => {
        rest.post.and.returnValue(of(new WebReaction(true, "{}", null)));
        service.update("a b", {enabled: false}).subscribe();
        expect(rest.post).toHaveBeenCalledWith("/server/pathpairs/update/a%20b", {enabled: false});
    });

    it("remove posts to the delete url", () => {
        rest.post.and.returnValue(of(new WebReaction(true, "{}", null)));
        service.remove("abc").subscribe();
        expect(rest.post).toHaveBeenCalledWith("/server/pathpairs/delete/abc");
    });
});
