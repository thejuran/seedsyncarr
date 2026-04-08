import {Record} from "immutable";

import {ViewFile} from "./view-file";

/**
 * View file options
 * Describes display related options for view files
 */
interface IViewFileOptions {
    // Method to use to sort the view file list
    sortMethod: ViewFileOptions.SortMethod;

    // Status filter setting
    selectedStatusFilter: ViewFile.Status | null;

    // Name filter setting
    nameFilter: string;
}


// Boiler plate code to set up an immutable class
const DefaultViewFileOptions: IViewFileOptions = {
    sortMethod: 0 as ViewFileOptions.SortMethod,
    selectedStatusFilter: null,
    nameFilter: "",
};
const ViewFileOptionsRecord = Record(DefaultViewFileOptions);


/**
 * Immutable class that implements the interface
 */
export class ViewFileOptions extends ViewFileOptionsRecord implements IViewFileOptions {
    sortMethod!: ViewFileOptions.SortMethod;
    selectedStatusFilter!: ViewFile.Status | null;
    nameFilter!: string;

    constructor(props: Partial<ViewFileOptions>) {
        super(props);
    }
}

export namespace ViewFileOptions {
    export enum SortMethod {
        STATUS,
        NAME_ASC,
        NAME_DESC
    }
}
