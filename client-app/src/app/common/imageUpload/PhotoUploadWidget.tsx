import { Grid, Header } from "semantic-ui-react";
import PhotoWidgetDropzone from "./PhotoWidgetDropzone";
import { useState } from "react";

export default function PhotoUploadWidget() {
    const [files, setFiles] = useState();
    return (
        <Grid>
            <Grid.Column width={4}>
                <Header sub color="teal" content="Step 1 - Add Photo" />
                <PhotoWidgetDropzone setFiles={setFiles} />
            </Grid.Column>
            <Grid.Column width={1} />
            <Grid.Column width={4}>
                <Header sub color="teal" content="Step 2 - Resize image" />
            </Grid.Column>
            <Grid.Column width={1} />
            <Grid.Column width={4}>
                <Header sub color="teal" content="Step 3 - Preview & Upload" />
            </Grid.Column>
        </Grid>
    )
}