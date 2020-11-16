import { Component, OnInit, Input } from "@angular/core";

@Component({
    selector: "app-welcome-dialog",
    templateUrl: "./welcome-dialog.component.html",
    styleUrls: [ "./welcome-dialog.css", "./welcome-dialog.responsivity.css" ]
})

export class WelcomeDialogComponent implements OnInit {

    constructor() {}
  data = [
    {
      "language": "en",
      "phrases": [ "My name is Anuja.", "Be welcome to my Live Resume.", "Down below, you will know me better... :)" ]
    }
    ];
    ngOnInit() {}
}
