import {Routes} from "@angular/router";
import {Type} from "@angular/core";

import * as Immutable from "immutable";

import {FilesPageComponent} from "./pages/files/files-page.component";
import {SettingsPageComponent} from "./pages/settings/settings-page.component";
import {LogsPageComponent} from "./pages/logs/logs-page.component";
import {AboutPageComponent} from "./pages/about/about-page.component";

export interface RouteInfo {
    path: string;
    name: string;
    component: Type<unknown>;
}

export const ROUTE_INFOS: Immutable.List<RouteInfo> = Immutable.List([
    {
        path: "dashboard",
        name: "Dashboard",
        component: FilesPageComponent
    },
    {
        path: "settings",
        name: "Settings",
        component: SettingsPageComponent
    },
    {
        path: "logs",
        name: "Logs",
        component: LogsPageComponent
    },
    {
        path: "about",
        name: "About",
        component: AboutPageComponent
    }
]);

export const ROUTES: Routes = [
    {
        path: "",
        redirectTo: "/dashboard",
        pathMatch: "full"
    },
    {
        path: "dashboard",
        component: FilesPageComponent
    },
    {
        path: "settings",
        component: SettingsPageComponent
    },
    {
        path: "logs",
        component: LogsPageComponent
    },
    {
        path: "about",
        component: AboutPageComponent
    }
];
