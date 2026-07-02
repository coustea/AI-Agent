import React, { createContext, useContext } from "react";
import type { RichVideoScene } from "../schema/types";

const SceneDataContext = createContext<RichVideoScene | null>(null);

export const SceneDataProvider: React.FC<{
  scene: RichVideoScene;
  children: React.ReactNode;
}> = ({ scene, children }) => (
  <SceneDataContext.Provider value={scene}>
    {children}
  </SceneDataContext.Provider>
);

export const useSceneData = () => useContext(SceneDataContext);
