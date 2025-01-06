import { Link } from "react-router-dom";
import { Container, Header, Segment, Image, Button } from "semantic-ui-react";
import { useStore } from "../../app/stores/store";
import { observer } from "mobx-react-lite";
import LoginForm from "../users/LoginForm";
import RegisterForm from "../users/RegisterForm";

export default observer(function HomePage() {
    const { userStore, modalStore } = useStore();
    return (
        <Segment inverted textAlign="center" vartical='true' className="masthead">
            <Container text>
                <Header as='h1' inverted>
                    <Image size='massive' src='/assets/logo.png' alt='logo' style={{ marginButtom: 12 }} />
                    Reactivities
                </Header>
                {userStore.isLoggedIn ? (
                    <>
                        <Header as='h2' inverted content='Welcome to Reactivities' />
                        <Button as={Link} to='/activities' size='huge' inverted>
                            Go to Activities!
                        </Button>
                    </>
                ) : (
                    <>
                        <Button onClick={() => modalStore.openModal(<LoginForm />)} size='huge' inverted>
                            Login!
                        </Button>
                        <Button onClick={() => modalStore.openModal(<RegisterForm />)} size='huge' inverted>
                            Register!
                        </Button>
                        <Button onClick={() => modalStore.openModal(<LoginForm prefilledEmail="bob@test.com" prefilledPassword="Pa$$w0rd" />)} size='huge' inverted>
                            For test login as bob!
                        </Button>
                    </>
                )}
                <div style={{ marginTop: '20px', textAlign: 'center' }}>
                    <a href="https://github.com/navidasadipur/Reactivites" target="_blank" rel="noopener noreferrer" style={{ color: 'white' }}>
                        View the source code on GitHub!
                    </a>
                </div>
            </Container>
        </Segment>
    )
})