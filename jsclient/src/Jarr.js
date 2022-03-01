import React from "react";
import PropTypes from "prop-types";
import { connect } from "react-redux";

import { ThemeProvider } from "@mui/styles";

import {jarrTheme, jarrLoginTheme} from "./Jarr.theme";
import NoAuth from "./features/noauth/NoAuth";
import TopMenu from "./features/topmenu/TopMenu";
import FeedList from "./features/feedlist/FeedList";
import EditPanel from "./features/editpanel/EditPanel";
import ClusterList from "./features/clusterlist/ClusterList";

function mapStateToProps(state) {
  return { isLogged: !!state.auth.token, };
}

function Jarr({ isLogged }) {
  let theme, content;
  if (!isLogged) {
    theme = jarrLoginTheme;
    content = <NoAuth />;
  } else {
    theme = jarrTheme;
    content = (
      <>
        <TopMenu />
        <FeedList />
        <ClusterList />
        <EditPanel />
      </>
    );
  }
  return <ThemeProvider theme={theme}>{content}</ThemeProvider>;
}

Jarr.propTypes = {
  isLogged: PropTypes.bool.isRequired,
};

export default connect(mapStateToProps)(Jarr);
