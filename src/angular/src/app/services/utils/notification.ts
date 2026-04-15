import {Record} from "immutable";

interface INotification {
    level: Notification.Level;
    text: string;
    timestamp: number;
    dismissible: boolean;
}
const DefaultNotification: INotification = {
    level: "info" as Notification.Level,
    text: "",
    timestamp: 0,
    dismissible: false,
};
const NotificationRecord = Record(DefaultNotification);


export class Notification extends NotificationRecord implements INotification {
    level!: Notification.Level;
    text!: string;
    timestamp!: number;
    dismissible!: boolean;

    constructor(props: Partial<Notification>) {
        super({...props, timestamp: Date.now()});
    }
}


export namespace Notification {
    export enum Level {
        SUCCESS         = "success",
        INFO            = "info",
        WARNING         = "warning",
        DANGER          = "danger",
    }
}
